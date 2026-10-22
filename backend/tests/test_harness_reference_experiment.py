import argparse
import copy
import json
from dataclasses import replace

import httpx
import pytest
from pydantic import ValidationError
from test_generate_workflow import FakeProvider

from app.application import workflow
from app.application.ai_provider import MalformedProviderResponseError, StructuredRequest

try:
    from app.application.workflow import _GroundedEvaluationOutput, _PlanningOutput
    from scripts import compare_harness_references as experiment
except ImportError:
    if hasattr(workflow, "_GroundedEvaluationOutput"):
        raise
    pytest.skip("Historical contract removed; run these tests on source commit e5198db",
                allow_module_level=True)


def source_case():
    return next(case for case in json.loads(experiment.CASES.read_text())
                if case["id"] == "duplicate-section-names")


def setup_review():
    planning = experiment.planning_artifact(source_case())
    source = experiment.snapshot(planning)
    baseline = experiment.review_request(planning, "qwen2.5:3b")
    return planning, source, baseline, experiment.candidate_request(baseline, source)


def feedback(section, quote, **changes):
    return {"strengths": [{"section": section, "quote": quote, "reason": "A specific effect."}],
            "weaknesses": [], "rubric_scores": dict.fromkeys([
                "story_clarity", "character", "conflict", "emotional_impact", "ending",
                "production_feasibility"], 4), "passed": True, **changes}


def test_candidate_preserves_author_context_draft_and_substantive_prompt():
    planning, source, baseline, candidate = setup_review()
    assert experiment._planning_input(planning) in candidate.input_text
    assert planning.creator_context in candidate.input_text
    assert baseline.response_model is _GroundedEvaluationOutput
    baseline_schema = baseline.response_model.model_json_schema()
    candidate_schema = candidate.response_model.model_json_schema()
    for name in ("kind", "quote", "author_quote", "suggestion", "reason"):
        old = baseline_schema["$defs"]["_GroundedWeakness"]["properties"][name]
        new = candidate_schema["$defs"]["TargetWeakness"]["properties"][name]
        assert old == new
    assert [item["content"] for item in source["targets"]][2:] == [s.content for s in planning.sections]
    assert candidate.response_model.model_validate(feedback(source["targets"][0]["key"], planning.title))
    for line in baseline.instructions.splitlines():
        if "section là tên" not in line and "section và quote" not in line:
            assert line in candidate.instructions


def test_duplicate_titles_are_unambiguous_and_production_baseline_is_unchanged():
    planning, source, _, candidate = setup_review()
    first, second = source["targets"][2:4]
    assert first["label"] == second["label"] == "Beat"
    assert first["key"] != second["key"]
    output = feedback(first["key"], first["content"])
    parsed = candidate.response_model.model_validate(output).model_dump()
    experiment.validate_feedback(parsed, planning, source, "target_keys", source["sha256"])
    with pytest.raises(MalformedProviderResponseError):
        experiment.validate_feedback(feedback("Beat", first["content"]), planning, source,
                                     "baseline", source["sha256"])


def test_wrong_target_and_cross_snapshot_key_fail_even_with_a_real_quote():
    planning, source, baseline, candidate = setup_review()
    first, second = source["targets"][2:4]
    output = feedback(second["key"], first["content"])
    with pytest.raises(MalformedProviderResponseError):
        experiment.validate_feedback(output, planning, source, "target_keys", source["sha256"])
    assert experiment.feedback_errors(output, planning, source, "target_keys")[0]["kind"] == "draft_quote"
    other = experiment.snapshot(replace(planning, creator_context='{"idea":"Different brief"}'))
    with pytest.raises(ValidationError):
        candidate.response_model.model_validate(feedback(other["targets"][0]["key"], planning.title))
    with pytest.raises(ValueError, match="different snapshot"):
        experiment.validate_feedback(output, planning, source, "target_keys", other["sha256"])
    assert baseline.response_model is _GroundedEvaluationOutput


def test_ai_question_is_not_author_evidence_and_all_error_classes_are_preserved():
    planning, source, _, _ = setup_review()
    planning = replace(planning, creator_context=json.dumps({
        "idea": "Keep the apartment.", "clarifications": [
            {"question": "Do you want an airport?", "answer": "Not decided."}]}))
    source = experiment.snapshot(planning)
    item = {"kind": "contradiction", "section": source["targets"][2]["key"],
            "quote": source["targets"][2]["content"], "reason": "A mismatch.",
            "author_quote": "Do you want an airport?", "suggestion": "An example."}
    output = feedback("fake", "fake", weaknesses=[item])
    errors = experiment.feedback_errors(output, planning, source, "target_keys")
    assert {e["kind"] for e in errors} == {"target_reference", "author_quote"}
    item["author_quote"] = ""
    assert "missing_author_quote" in {e["kind"] for e in experiment.feedback_errors(output, planning, source, "target_keys")}


def test_malformed_output_keeps_raw_text_and_does_not_retry():
    _, source, _, candidate = setup_review()
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"done": True, "model": "qwen2.5:3b",
                                       "message": {"content": '{"invalid":true}'}})

    with httpx.Client(base_url="http://localhost", transport=httpx.MockTransport(handler)) as client:
        row = experiment.call_model(client, candidate, "qwen2.5:3b", 42)
    assert len(calls) == 1
    assert not row["schema_valid"]
    assert row["raw_output"] == '{"invalid":true}'
    assert row["errors"][0]["kind"] == "schema"
    assert source["sha256"]


def test_fixture_scope_and_planner_request_uses_current_profile():
    cases = json.loads(experiment.CASES.read_text())
    assert sum(case["operation"] == "review" for case in cases) == 12
    assert sum(case["operation"] == "plan" for case in cases) == 4
    case = next(case for case in cases if case["operation"] == "plan")
    request = experiment.planning_request(case, "qwen2.5:3b")
    assert request.stage == "planning"
    assert request.response_model is _PlanningOutput
    assert case["idea"] in request.input_text


@pytest.mark.parametrize("execution_model", ["qwen2.5:3b", "qwen2.5:7b"])
def test_runner_resume_shares_plans_and_never_opens_stores(tmp_path, monkeypatch, execution_model):
    from app.application import dataset

    monkeypatch.setattr(dataset, "get_dataset_store", lambda: pytest.fail("Opened dataset store"))
    cases = json.loads(experiment.CASES.read_text())
    selected = [source_case(), next(c for c in cases if c["operation"] == "plan")]
    source_path = tmp_path / "cases.json"
    source_path.write_text(json.dumps(selected))
    calls = []
    profile_models = []
    original_planning_request = experiment.planning_request

    def capture_profile(case, model):
        profile_models.append(model)
        return original_planning_request(case, model)

    monkeypatch.setattr(experiment, "planning_request", capture_profile)
    fake_plan = FakeProvider().request_structured(StructuredRequest("", "", _PlanningOutput)).output

    def handler(request):
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": execution_model, "digest": "fake"}]})
        if request.url.path == "/api/ps":
            return httpx.Response(200, json={"models": []})
        body = json.loads(request.content)
        calls.append(body)
        if body["format"]["title"] == "_PlanningOutput":
            output = fake_plan.model_dump()
        else:
            input_text = body["messages"][1]["content"]
            draft, _ = json.JSONDecoder().raw_decode(input_text.split("Current draft (JSON data):\n")[1])
            section = draft["sections"][0]
            anchor = section["title"]
            if body["format"]["title"] == "TargetEvaluation":
                mapping, _ = json.JSONDecoder().raw_decode(input_text.split("counted from 1):\n")[1])
                anchor = mapping[2]["key"]
            output = feedback(anchor, section["content"])
        return httpx.Response(200, json={"done": True, "model": execution_model,
                                       "message": {"content": json.dumps(output)}})

    original_client = httpx.Client
    monkeypatch.setattr(experiment.httpx, "Client", lambda **kwargs: original_client(
        **kwargs, transport=httpx.MockTransport(handler)))
    args = argparse.Namespace(cases=source_path, model=execution_model, seeds=[42, 73],
                              request_profile_model="qwen2.5:3b",
                              case_ids=None, timeout=180, resume=False, output=tmp_path / "out.json")
    report = experiment.run(args)
    assert len(report["plans"]) == 2
    assert len(report["results"]) == 8
    assert len(calls) == 10
    assert all(body["model"] == execution_model for body in calls)
    assert profile_models == ["qwen2.5:3b", "qwen2.5:3b"]
    expected = original_planning_request(selected[1], "qwen2.5:3b")
    planning_body = next(body for body in calls if body["format"]["title"] == "_PlanningOutput")
    assert planning_body["messages"][0]["content"] == experiment.strict_json_instructions(expected)
    assert planning_body["messages"][1]["content"] == expected.input_text
    if execution_model != "qwen2.5:3b":
        assert report["configuration"]["request_profile_model"] == "qwen2.5:3b"
    before = len(calls)
    args.resume = True
    assert experiment.run(args)["summary"] == report["summary"]
    assert len(calls) == before
    assert [row["variant"] for row in report["results"]] == [
        "baseline", "target_keys", "target_keys", "baseline",
        "target_keys", "baseline", "baseline", "target_keys"]
    blinded, review_key = experiment.blinded_review(report)
    assert len(blinded) == len(review_key) == 8
    assert all("variant" not in row for row in blinded)
    args.seeds = [101]
    with pytest.raises(ValueError, match="configuration differs"):
        experiment.run(args)


@pytest.mark.parametrize("failure", [
    "source", "source_missing", "digest", "missing_model", "response_model",
])
@pytest.mark.parametrize("operation", ["review", "plan"])
def test_runner_invalidates_drift_and_preserves_evidence(tmp_path, monkeypatch, failure, operation):
    cases = json.loads(experiment.CASES.read_text())
    selected = next(case for case in cases if case["operation"] == operation)
    source_path = tmp_path / "cases.json"
    source_path.write_text(json.dumps([selected]))
    calls = []
    tags = []
    def hashes():
        if calls and failure == "source_missing":
            raise FileNotFoundError("Source removed")
        return {"source": "changed" if calls and failure == "source" else "frozen"}

    monkeypatch.setattr(experiment, "source_hashes", hashes)
    fake_plan = FakeProvider().request_structured(StructuredRequest("", "", _PlanningOutput)).output

    def handler(request):
        if request.url.path == "/api/tags":
            tags.append(request)
            model = {"name": "qwen2.5:3b", "digest": "frozen"}
            if len(tags) > 1:
                if failure == "digest":
                    model["digest"] = "changed"
                elif failure == "missing_model":
                    return httpx.Response(200, json={"models": []})
            return httpx.Response(200, json={"models": [model]})
        if request.url.path == "/api/ps":
            return httpx.Response(200, json={"models": []})
        body = json.loads(request.content)
        calls.append(body)
        output = (fake_plan.model_dump() if body["format"]["title"] == "_PlanningOutput"
                  else feedback("logline", "not an actual quote"))
        return httpx.Response(200, json={
            "done": True,
            "model": "unexpected-model" if failure == "response_model" else "qwen2.5:3b",
            "message": {"content": json.dumps(output)},
        })

    original_client = httpx.Client
    monkeypatch.setattr(experiment.httpx, "Client", lambda **kwargs: original_client(
        **kwargs, transport=httpx.MockTransport(handler)))
    args = argparse.Namespace(cases=source_path, model="qwen2.5:3b", seeds=[42],
                              request_profile_model=None, case_ids=None, timeout=180,
                              resume=False, output=tmp_path / "out.json")
    with pytest.raises(ValueError, match="Invalid experiment"):
        experiment.run(args)
    report = json.loads(args.output.read_text())
    assert report["status"] == "invalid"
    assert report["integrity_errors"]
    recorded = [*report["plans"], *report["results"]]
    assert len(recorded) == len(calls)
    assert all(row["raw_output"] for row in recorded)
    if failure in {"source", "source_missing", "response_model"}:
        assert len(calls) == 1
    if failure == "response_model":
        assert not recorded[0]["schema_valid"]
        assert not recorded[0]["runtime_accepted"]
        assert recorded[0]["errors"] == [{"kind": "model_mismatch"}]
    args.resume = True
    with pytest.raises(ValueError, match="cannot be resumed"):
        experiment.run(args)
    assert len(calls) == len(recorded)


@pytest.mark.parametrize("target_index", [0, 1, 2, 3])
def test_blinding_normalizes_both_arms_without_changing_raw_report(target_index):
    _, source, _, _ = setup_review()
    target = source["targets"][target_index]
    unknown = "000000000000:section-999"
    rows = []
    for variant, anchor in [("baseline", target["label"]), ("target_keys", target["key"])]:
        rows.append({"case_id": "same-case", "seed": 42, "variant": variant,
                     "snapshot": source, "output": feedback(anchor, target["content"], weaknesses=[{
                         "section": anchor, "quote": target["content"], "kind": "craft",
                         "reason": f"Read {target['key'] if variant == 'target_keys' else target['label']}.",
                         "author_quote": "", "suggestion": f"Avoid {unknown}.",
                     }])})
    report = {"results": rows}
    original = copy.deepcopy(report)
    blinded, review_key = experiment.blinded_review(report)
    assert report == original
    assert len(blinded) == len(review_key) == 2
    assert blinded[0]["output"] == blinded[1]["output"]
    assert all(row["output"]["strengths"][0]["section"] == target["label"] for row in blinded)
    assert unknown not in json.dumps(blinded)
    assert source["sha256"][:12] not in json.dumps(blinded)
    assert {item["variant"] for item in review_key.values()} == {"baseline", "target_keys"}
    assert all(set(row) == {"review_id", "case_id", "source", "creator_context", "output"}
               for row in blinded)
    assert {row["review_id"] for row in blinded} == set(review_key)
    again, _ = experiment.blinded_review(report)
    assert not {row["review_id"] for row in blinded} & {row["review_id"] for row in again}


@pytest.mark.parametrize("variant,anchor", [
    ("baseline", "Logline"),
    ("target_keys", "000000000000:section-999"),
    ("target_keys", "Beat"),
])
def test_blinding_uses_the_same_marker_for_invalid_anchors(variant, anchor):
    _, source, _, _ = setup_review()
    report = {"results": [{"case_id": "invalid", "seed": 42, "variant": variant,
                           "snapshot": source, "output": feedback(anchor, "some quote")} ]}
    blinded, _ = experiment.blinded_review(report)
    assert blinded[0]["output"]["strengths"][0]["section"] == "[unavailable target]"


def test_reexport_preserves_ids_and_refuses_partial_or_mismatched_files(tmp_path):
    _, source, _, _ = setup_review()
    report = {"results": [{"case_id": "export", "seed": 42, "variant": "baseline",
                           "snapshot": source, "output": feedback("title", "A quote")} ]}
    output = tmp_path / "report.json"
    blinded_path = output.with_suffix(".blinded.json")
    key_path = output.with_suffix(".review-key.json")
    experiment.export_blinded_review(report, output)
    original = {path: path.read_bytes() for path in [blinded_path, key_path]}
    experiment.export_blinded_review(report, output)
    assert all(path.read_bytes() == content for path, content in original.items())
    key_path.unlink()
    with pytest.raises(FileExistsError, match="Incomplete review export"):
        experiment.export_blinded_review(report, output)
    assert blinded_path.read_bytes() == original[blinded_path]
    key_path.write_text("{}")
    with pytest.raises(ValueError, match="does not match"):
        experiment.export_blinded_review(report, output)
    assert key_path.read_text() == "{}"
    assert blinded_path.read_bytes() == original[blinded_path]
