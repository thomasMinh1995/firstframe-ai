from copy import deepcopy
import json

import pytest
from pydantic import ValidationError

from app.application.ai_provider import MalformedProviderResponseError
from app.application.revision_review import review_context
from app.application.workflow import _card_review_schema, revision_evaluation
from test_revision_review import context_fixture
from test_projects import develop_project, project_client, start_project


def checked_output(context, comparison="aligned", suggestion=""):
    return dict(reviews=[dict(card_id="section-3-part-1", related_card_id="section-3",
        decision_id="answer-1", comparison=comparison, observation="Đối chiếu điểm dừng.",
        suggestion=suggestion)], passed=True, rubric_scores=None, decision_checks=[dict(
            decision_id=d["id"], draft_comparison="aligned", card_ids=["section-3-part-1"],
            draft_reason="Chi tiết giữ lựa chọn trong đoạn đang xét.",
            suggestion_comparison="aligned" if suggestion else "not_applicable",
            suggestion_reason="Chỉ dẫn giữ lựa chọn." if suggestion else "Không có suggestion.")
        for d in context["decisions"]])


def evaluate(raw, context):
    return revision_evaluation(_card_review_schema(context).model_validate(raw), context)


def test_new_runtime_requires_checks_after_reviews():
    context = review_context(*context_fixture(), True)
    raw = checked_output(context)
    del raw["decision_checks"]
    with pytest.raises(ValidationError):
        _card_review_schema(context).model_validate(raw)
    fields = list(_card_review_schema(context).model_json_schema()["properties"])
    assert fields.index("reviews") < fields.index("decision_checks")


@pytest.mark.parametrize("case", [
    "missing", "duplicate", "unknown", "outside", "empty_evidence", "blank_reason",
    "hidden_mismatch", "wrong_decision", "uncertain_aligned", "cited_not_applicable",
    "unsafe_suggestion", "unverified_suggestion", "checks_nonexistent_suggestion",
    "unrelated_evidence", "aligned_without_evidence",
])
def test_rejects_incomplete_or_inconsistent_checks(case):
    context = review_context(*context_fixture(), True)
    raw = checked_output(context)
    checks = raw["decision_checks"]
    if case == "missing":
        checks.pop()
    elif case == "duplicate":
        checks[0] = deepcopy(checks[1])
    elif case == "unknown":
        checks[0]["decision_id"] = "invented"
    elif case == "outside":
        checks[0]["card_ids"] = ["section-1"]
    elif case == "blank_reason":
        checks[0]["draft_reason"] = " "
    elif case == "hidden_mismatch":
        checks[0]["draft_comparison"] = "mismatch"
    elif case == "wrong_decision":
        raw = checked_output(context, "mismatch", "Bỏ phần sau điểm dừng.")
        raw["decision_checks"][0]["draft_comparison"] = "mismatch"
    elif case == "uncertain_aligned":
        checks[0]["draft_comparison"] = "uncertain"
    elif case == "cited_not_applicable":
        checks[-1]["draft_comparison"] = "not_applicable"
    elif case == "aligned_without_evidence":
        checks[-1]["card_ids"] = []
    elif case in {"unsafe_suggestion", "unverified_suggestion"}:
        raw = checked_output(context, "uncertain", "Tác giả muốn dừng ở đâu?")
        raw["decision_checks"][0]["suggestion_comparison"] = (
            "mismatch" if case == "unsafe_suggestion" else "uncertain")
    elif case == "checks_nonexistent_suggestion":
        checks[0]["suggestion_comparison"] = "aligned"
    elif case == "empty_evidence":
        raw = checked_output(context, "mismatch", "Bỏ phần sau điểm dừng.")
        raw["decision_checks"][-1].update(draft_comparison="mismatch", card_ids=[])
    elif case == "unrelated_evidence":
        # Another scoped edited card cannot stand in for the review's cited evidence.
        context["focus_card_ids"].append("section-2")
        raw = checked_output(context, "mismatch", "Bỏ phần sau điểm dừng.")
        raw["decision_checks"][-1].update(draft_comparison="mismatch", card_ids=["section-2"])
    with pytest.raises((ValidationError, MalformedProviderResponseError)):
        evaluate(raw, context)


@pytest.mark.parametrize("comparison,suggestion", [
    ("aligned", ""), ("uncertain", ""), ("uncertain", "Bạn muốn dừng khi nào?"),
    ("mismatch", "Gộp hai lần bắt máy, giữ điểm dừng."),
])
def test_keeps_valid_neutral_and_continuity_reviews(comparison, suggestion):
    context = review_context(*context_fixture(), True)
    original = deepcopy(context)
    raw = checked_output(context, comparison, suggestion)
    # An unrelated answer need not become the source of the main review.
    raw["decision_checks"][1].update(draft_comparison="not_applicable", card_ids=[])
    if comparison == "uncertain":
        raw["decision_checks"][-1]["draft_comparison"] = "uncertain"
    result = evaluate(raw, context)
    assert result.passed is (None if comparison == "uncertain" else comparison == "aligned")
    assert context == original


def test_explicit_violation_cites_its_check_and_keeps_all_decisions():
    context = review_context(*context_fixture(), True)
    raw = checked_output(context, "mismatch", "Dừng khi vừa bắt máy.")
    raw["decision_checks"][-1]["draft_comparison"] = "mismatch"
    assert evaluate(raw, context).passed is False


def test_all_supplied_constraints_remain_required_without_truncation():
    draft, previous, author = context_fixture()
    author["constraints"] = [f"Giới hạn tác giả {i}." for i in range(20)]
    context = review_context(draft, previous, author, True)
    raw = checked_output(context)
    parsed = _card_review_schema(context).model_validate(raw)
    assert len(parsed.decision_checks) == len(context["decisions"]) == 23
    assert revision_evaluation(parsed, context).passed is True


def test_new_dataset_cannot_fall_back_to_legacy_or_change_recorded_check_ids():
    from app.application.dataset_corrections import validate_corrections
    context = review_context(*context_fixture(), True)
    schema = _card_review_schema(context).model_json_schema()
    raw = checked_output(context)
    step = dict(stage="evaluation", status="completed", output={}, request=dict(
        response_schema=schema, input_text="Card review context (JSON data):\n" + json.dumps(context)))
    sample = dict(status="completed", steps=[step])
    assert validate_corrections(sample, {"0": raw})["0"]["decision_checks"] == raw["decision_checks"]
    missing = deepcopy(raw)
    missing.pop("decision_checks")
    with pytest.raises(ValueError):
        validate_corrections(sample, {"0": missing})
    item = schema["properties"]["decision_checks"]["items"]
    fields = schema["$defs"][item["$ref"].split("/")[-1]]["properties"]
    fields["decision_id"] = {"const": "answer-1"}
    with pytest.raises(ValueError):
        validate_corrections(sample, {"0": raw})


@pytest.mark.parametrize("failure", ["missing_item", "legacy_shape", "unsafe_suggestion"])
def test_failed_check_preserves_saved_draft_feedback_and_never_retries(project_client, monkeypatch, failure):
    from app.application.workflow import _RevisionReviewOutput
    from dataclasses import replace
    client, provider = project_client
    project = develop_project(client, start_project(client))
    before_calls = len(provider.requests)
    original = provider.request_structured

    def invalid(request):
        result = original(request)
        if failure == "missing_item":
            result.output.decision_checks.pop()
        elif failure == "legacy_shape":
            result = replace(result, output=_RevisionReviewOutput.model_validate(
                result.output.model_dump(exclude={"decision_checks"})))
        else:
            result.output.reviews[0].comparison = "uncertain"
            result.output.reviews[0].suggestion = "Thêm một hành động mới."
            result.output.decision_checks[0].suggestion_comparison = "uncertain"
        return result

    monkeypatch.setattr(provider, "request_structured", invalid)
    url = f"/api/projects/{project['id']}"
    response = client.post(url + "/review", json={"revision": project["revision"]})
    assert response.status_code == 502
    assert client.get(url).json() == project
    assert len(provider.requests) == before_calls + 1
