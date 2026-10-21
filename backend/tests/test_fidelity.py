import copy
import json

import pytest

from app.application.ai_provider import ProviderMetadata, StructuredResult
from app.application.fidelity import EvidenceIssue, cited_check, evidence_spans
from app.application.workflow import create_story_generation_service
from app.core.artifacts import PlanSection

AUTHOR = {"idea": "Người kể làm lab coach.", "constraints": ["Giữ kết quả tuyển dụng chưa biết."]}
DRAFT = {
    "title": "AI chông gai",
    "logline": "Học AI.",
    "sections": [
        {"title": "Middle", "content": "🙂 Người kể quyết định pass. Người kể hướng dẫn bài lab."},
        {"title": "Ending", "content": "Email chưa mở."},
    ],
}


class ScriptedProvider:
    metadata = ProviderMetadata("fake", "fidelity-test")

    def __init__(self, replies):
        self.replies = iter(replies)
        self.requests = []

    def request_structured(self, request):
        self.requests.append(request)
        reply = next(self.replies)
        if callable(reply):
            reply = reply(json.loads(request.input_text))
        return StructuredResult(output=request.response_model.model_validate(reply), model="test")


def review(provider, draft=DRAFT):
    return create_story_generation_service(provider).review(
        AUTHOR["idea"],
        draft["title"],
        draft["logline"],
        tuple(
            PlanSection(str(i), s["title"], "", s["content"])
            for i, s in enumerate(draft["sections"])
        ),
        json.dumps(AUTHOR, ensure_ascii=False),
        response_language="vi",
    )


def issue():
    authors, drafts = evidence_spans(DRAFT, AUTHOR)
    return {
        "author_span_id": next(k for k, v in authors.items() if "tuyển dụng" in v),
        "draft_span_id": next(k for k, v in drafts.items() if "quyết định pass" in v["text"]),
        "explanation": "Kết quả tuyển dụng bị biến thành hành động tự quyết.",
        "suggestion": "Cho người kể tiếp tục hướng dẫn lab, không công bố kết quả.",
    }


def audit(verdict="supported", **changes):
    return {
        "draft_span_id": issue()["draft_span_id"],
        "author_span_id": issue()["author_span_id"],
        "relation": "contradictory" if verdict == "supported" else "uncertain",
        "relation_reason": "Đối chiếu hai nguồn.",
        "concern": {"supported": "supported", "contradicted": "unsupported", "uncertain": "uncertain"}[verdict],
        "concern_reason": "Giữ việc hướng dẫn và kết quả chưa biết.",
        "revision": "aligned" if verdict == "supported" else "uncertain",
        "revision_reason": "Giữ kết mở.",
        **changes,
    }


def test_fidelity_runs_before_criticism_and_keeps_exact_snapshot_and_quotes():
    before = copy.deepcopy(DRAFT)
    provider = ScriptedProvider([{"status": "issues", "issues": [issue()]}, audit()])
    result = review(provider)
    assert [r.stage for r in provider.requests] == ["fidelity", "fidelity_audit"]
    assert result.fidelity["status"] == "issues"
    check = result.fidelity["checks"][0]
    assert check["section_index"] == 0 and check["section_title"] == "Middle"
    assert check["draft_quote"] == "🙂 Người kể quyết định pass."
    assert check["section_text"] == DRAFT["sections"][0]["content"]
    assert check["suggestion"] == issue()["suggestion"]
    assert check["suggestion_status"] == "supported"
    assert check["assessment"]["revision_reason"]
    assert DRAFT == before
    assert not result.findings and result.passed is None


@pytest.mark.parametrize(
    "change",
    [
        {"draft_span_id": "invented"},
        {"author_span_id": "invented"},
    ],
)
def test_invented_evidence_stops_before_criticism(change):
    provider = ScriptedProvider([{"status": "issues", "issues": [{**issue(), **change}]}])
    result = review(provider)
    assert len(provider.requests) == 1
    assert result.fidelity["status"] == "unverified"
    assert result.fidelity["checks"] == [] and not result.findings


@pytest.mark.parametrize(
    "changes",
    [
        {"draft_span_id": "d0"},
        {"author_span_id": "a0"},
        {"concern": "unsupported"},
    ],
)
def test_unverified_or_silently_rewritten_suggestions_are_withheld(changes):
    provider = ScriptedProvider([{"status": "issues", "issues": [issue()]}, audit(**changes)])
    result = review(provider)
    assert result.fidelity["status"] == "unverified"
    assert result.fidelity["withheld_count"] == 1
    assert all(check["suggestion"] is None for check in result.fidelity["checks"])
    assert not result.findings and result.passed is None


def test_corrected_draft_still_audits_artistic_suggestions_and_hides_bad_scores():
    critic = {
        "passed": True,
        "rubric_scores": dict.fromkeys(
            [
                "story_clarity",
                "character",
                "conflict",
                "emotional_impact",
                "ending",
                "production_feasibility",
            ],
            2,
        ),
        "strengths": [],
        "weaknesses": ["Chưa có kết quả."],
        "suggestions": ["Công bố kết quả tuyển dụng."],
    }
    rejected = audit("contradicted")
    provider = ScriptedProvider([{"status": "clear", "issues": []}, critic, rejected])
    corrected = copy.deepcopy(DRAFT)
    corrected["sections"][0]["content"] = "Người kể tiếp tục hướng dẫn lab."
    result = review(provider, corrected)
    assert [r.stage for r in provider.requests] == ["fidelity", "evaluation", "fidelity_audit"]
    assert not result.findings and result.passed is None
    assert result.fidelity["withheld_count"] == 1


def test_ambiguous_quote_or_quote_from_wrong_source_is_not_highlightable():
    draft = copy.deepcopy(DRAFT)
    draft["sections"][0]["content"] = "Lặp. Lặp."
    item = EvidenceIssue(
        section_index=0,
        draft_quote="Lặp.",
        author_quote=AUTHOR["idea"],
        explanation="Test",
        suggestion="Test",
    )
    assert cited_check(item, draft, AUTHOR) is None
    item.draft_quote = DRAFT["sections"][0]["content"]
    item.author_quote = "Không có trong ý đồ."
    assert cited_check(item, DRAFT, AUTHOR) is None


def test_project_save_reopen_and_language_change_preserve_review_snapshot(project_client):
    from test_projects import develop_project, payload, start_project

    client, _ = project_client
    project = develop_project(client, start_project(client))
    original = copy.deepcopy(project["feedback"]["fidelity"])
    assert original["checks"]
    url = f"/api/projects/{project['id']}"
    edits = payload(project)
    edits["draft"]["sections"][0]["content"] = "BẢN MỚI chưa được review."
    edits["response_language"] = "en"
    saved = client.put(url, json=edits).json()
    assert saved["draft"] == edits["draft"] and not saved["feedback_is_current"]
    assert saved["feedback"]["fidelity"] == original
    reopened = client.get(url).json()
    assert reopened["feedback"]["fidelity"] == original
    assert reopened["versions"][-1]["feedback"]["fidelity"] == original


pytest_plugins = ["test_projects"]


def test_questions_are_context_not_citable_author_decisions():
    author = {
        "idea": "Chờ kết quả.",
        "clarifications": [{"question": "Công bố kết quả?", "answer": "Để quyết định sau."}],
    }
    spans, _ = evidence_spans(DRAFT, author)
    assert "Công bố kết quả?" not in spans.values()
    assert "Để quyết định sau." in spans.values()
    provider = ScriptedProvider(
        [
            {"status": "clear", "issues": []},
            {
                "passed": True,
                "rubric_scores": dict.fromkeys(
                    [
                        "story_clarity",
                        "character",
                        "conflict",
                        "emotional_impact",
                        "ending",
                        "production_feasibility",
                    ],
                    4,
                ),
                "strengths": [],
                "weaknesses": [],
                "suggestions": [],
            },
        ]
    )
    create_story_generation_service(provider).review(
        author["idea"], "Title", "Logline", (), json.dumps(author), response_language="vi"
    )
    assert json.loads(provider.requests[0].input_text)["author_context"] == author


def test_failed_audit_preserves_saved_edits_and_previous_feedback(project_client, monkeypatch):
    from test_projects import develop_project, payload, start_project

    from app.application.ai_provider import ProviderTimeoutError

    client, provider = project_client
    project = develop_project(client, start_project(client))
    url = f"/api/projects/{project['id']}"
    data = payload(project)
    data["draft"]["sections"][0]["content"] = "Bản đã sửa, giữ lab coach."
    saved = client.put(url, json=data).json()
    original = provider.request_structured

    def timeout(request):
        if request.stage == "fidelity_audit":
            raise ProviderTimeoutError("audit timeout")
        return original(request)

    monkeypatch.setattr(provider, "request_structured", timeout)
    response = client.post(f"{url}/review", json={"revision": saved["revision"]})
    assert response.status_code == 504
    assert client.get(url).json() == saved


def test_long_unpunctuated_quote_remains_exact():
    draft = copy.deepcopy(DRAFT)
    draft["sections"][0]["content"] = "🙂" * 3000
    authors, spans = evidence_spans(draft, AUTHOR)
    from app.application.fidelity import SpanIssue, resolve_span

    resolved = resolve_span(
        SpanIssue(
            author_span_id="a0",
            draft_span_id=next(k for k, v in spans.items() if v["section_index"] == 0),
            explanation="Test",
            suggestion="Test",
        ),
        authors,
        spans,
    )
    assert cited_check(resolved, draft, AUTHOR).draft_quote == "🙂" * 3000


def test_replay_preserves_evidence_and_never_overwrites(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from app.core.artifacts import ArtifactMetadata, EvaluationArtifact
    from scripts.replay_fidelity import replay

    captured = []

    def review(*args, **kwargs):
        captured.append((args, kwargs))
        return EvaluationArtifact(
            ArtifactMetadata("id", "short-film", "evaluation"),
            "plan",
            fidelity={"status": "clear", "checks": [], "withheld_count": 0},
        )

    monkeypatch.setattr(
        "scripts.replay_fidelity.create_story_generation_service",
        lambda provider: SimpleNamespace(review=review),
    )
    source = tmp_path / "source.jsonl"
    source.write_text(
        json.dumps(
            {
                "operation": "test",
                "input": {
                    "idea": AUTHOR["idea"],
                    "constraints": AUTHOR["constraints"],
                    "draft": DRAFT,
                    "response_language": "vi",
                },
            }
        )
    )
    output = tmp_path / "result.jsonl"
    replay(source, output)
    assert captured[0][0][3][0].content == DRAFT["sections"][0]["content"]
    assert json.loads(output.read_text())["output"]["fidelity"]["status"] == "clear"
    original = output.read_bytes()
    with pytest.raises(FileExistsError):
        replay(source, output)
    assert output.read_bytes() == original


def test_mismatched_critic_pairs_stop_before_audit_and_count_withheld_suggestions():
    critic = {
        "passed": True,
        "rubric_scores": dict.fromkeys(
            [
                "story_clarity",
                "character",
                "conflict",
                "emotional_impact",
                "ending",
                "production_feasibility",
            ],
            4,
        ),
        "strengths": [],
        "weaknesses": [],
        "suggestions": ["Gợi ý không có điểm yếu đi kèm."],
    }
    provider = ScriptedProvider([{"status": "clear", "issues": []}, critic])
    result = review(provider)
    assert [r.stage for r in provider.requests] == ["fidelity", "evaluation"]
    assert result.fidelity["withheld_count"] == 1
    assert not result.findings and result.passed is None


def test_rejected_allegation_is_not_shown_as_an_unresolved_finding():
    provider = ScriptedProvider([
        {"status": "issues", "issues": [issue()]}, audit("contradicted"),
    ])
    result = review(provider)
    assert result.fidelity == {"status": "unverified", "checks": [], "withheld_count": 1}


def test_uncertain_audit_preserves_its_reason_and_original_evidence():
    provider = ScriptedProvider([
        {"status": "issues", "issues": [issue()]},
        audit("uncertain", concern_reason="Chưa đủ căn cứ để kết luận."),
    ])
    result = review(provider)
    check = result.fidelity["checks"][0]
    assert check["assessment"]["concern_reason"] == "Chưa đủ căn cứ để kết luận."
    assert check["draft_quote"] == "🙂 Người kể quyết định pass."
    assert check["suggestion"] is None


def test_review_after_edit_anchors_new_snapshot_and_keeps_old_history(project_client, monkeypatch):
    from test_projects import develop_project, payload, start_project

    from app.api.routes import projects as routes

    client, _ = project_client
    project = develop_project(client, start_project(client))
    old_feedback = copy.deepcopy(project["feedback"])
    url = f"/api/projects/{project['id']}"
    data = payload(project)
    data["draft"]["sections"][0]["content"] = "BẢN ĐÃ SỬA: lab coach hướng dẫn bài lab."
    saved = client.put(url, json=data).json()

    def scan(payload):
        return {"status": "issues", "issues": [{
            "draft_span_id": next(k for k, v in payload["draft_spans"].items()
                                  if v["text"].startswith("BẢN ĐÃ SỬA")),
            "author_span_id": "a0", "explanation": "Test only", "suggestion": "Test only",
        }]}

    def approve(payload):
        return {**audit(),
                "draft_span_id": next(k for k, v in payload["draft_spans"].items()
                                      if v["text"].startswith("BẢN ĐÃ SỬA")),
                "author_span_id": "a0"}

    provider = ScriptedProvider([scan, approve])
    monkeypatch.setattr(routes, "get_story_generation_service",
                        lambda: create_story_generation_service(provider))
    response = client.post(f"{url}/review", json={"revision": saved["revision"]})
    assert response.status_code == 200, response.text
    reviewed = response.json()
    check = reviewed["feedback"]["fidelity"]["checks"][0]
    assert check["section_index"] == 0
    assert check["section_text"] == data["draft"]["sections"][0]["content"]
    assert check["draft_quote"] == check["section_text"]
    assert reviewed["feedback_is_current"]
    assert reviewed["versions"][0]["feedback"] == old_feedback
    assert client.get(url).json()["feedback"] == reviewed["feedback"]


@pytest.mark.parametrize("relation", ["contradictory", "compatible", "uncertain"])
@pytest.mark.parametrize("concern", ["supported", "unsupported", "uncertain"])
@pytest.mark.parametrize("revision", ["aligned", "violates", "uncertain"])
def test_independent_judgments_must_all_support_a_fidelity_revision(relation, concern, revision):
    provider = ScriptedProvider([
        {"status": "issues", "issues": [issue()]},
        audit(relation=relation, concern=concern, revision=revision),
    ])
    report = review(provider).fidelity
    allowed = relation == "contradictory" and concern == "supported" and revision == "aligned"
    assert any(c["suggestion"] is not None for c in report["checks"]) == allowed
    assert report["withheld_count"] == (0 if allowed else 1)
    if relation == "contradictory" and concern == "supported" and revision == "violates":
        assert report["checks"][0]["assessment"]["revision"] == "violates"
        assert report["checks"][0]["draft_quote"] == "🙂 Người kể quyết định pass."


def test_suite_is_balanced_frozen_and_excludes_story_specific_tuning():
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "demo/evaluations/fidelity-suite/cases.json"
    suite = json.loads(path.read_text())
    cases = suite["cases"]
    assert len(cases) == 24 and len({c["id"] for c in cases}) == 24
    assert {c["language"] for c in cases} == {"vi", "en"}
    assert sum(c["split"] == "holdout" for c in cases) == 8
    assert {c["expected"]["scan"] for c in cases} == {"clear", "issues", "uncertain"}
    assert "chông gai" not in path.read_text() and "lab coach" not in path.read_text()
    for family in {c["family"] for c in cases}:
        assert len({c["split"] for c in cases if c["family"] == family}) == 1
    for case in cases:
        candidate = case["candidate"]
        if case["id"] != "missing-intent":
            assert cited_check(EvidenceIssue(**candidate), case["draft"], case["author"])


def test_acceptance_runner_records_errors_without_overwriting_or_leaking_labels(tmp_path):
    from scripts.accept_fidelity import run_suite

    case = {"id": "one", "split": "holdout", "language": "vi", "author": AUTHOR,
            "draft": DRAFT, "candidate": {"section_index": 0,
            "draft_quote": "🙂 Người kể quyết định pass.", "author_quote": AUTHOR["constraints"][0],
            "explanation": "Sai quyền quyết định.", "suggestion": "Giữ kết mở."},
            "expected": {"scan": "issues", "relation": "contradictory", "concern": "supported",
                         "revision": "aligned", "allow_revision": True}}
    source = tmp_path / "cases.json"
    source.write_text(json.dumps({"label_status": "proposed", "cases": [case]}))
    output = tmp_path / "output.jsonl"
    provider = ScriptedProvider([{"status": "issues", "issues": [issue()]}, audit()])
    run_suite(source, output, provider)
    row = json.loads(output.read_text())
    assert row["scores"]["all_labels_match"]
    assert row["semantic_reason_review"] == "pending_human"
    assert all("expected" not in json.loads(r.input_text) for r in provider.requests)
    assert all(json.loads(r.input_text)["response_language"] == "Vietnamese"
               for r in provider.requests)
    before = output.read_bytes()
    with pytest.raises(FileExistsError):
        run_suite(source, output, provider)
    assert output.read_bytes() == before
    failed = tmp_path / "failed.jsonl"
    run_suite(source, failed, ScriptedProvider([]))
    assert json.loads(failed.read_text())["error"] == "StopIteration"


def test_acceptance_runner_can_audit_missing_author_evidence(tmp_path):
    from scripts.accept_fidelity import run_suite

    case = {"id": "missing-intent", "split": "holdout", "language": "vi",
            "author": {"idea": "", "constraints": []}, "draft": DRAFT,
            "candidate": {"section_index": 0, "draft_quote": "🙂 Người kể quyết định pass.",
                          "author_quote": "", "explanation": "Claim", "suggestion": "Change"},
            "expected": {"scan": "uncertain", "relation": "uncertain", "concern": "uncertain",
                         "revision": "uncertain", "allow_revision": False}}
    source = tmp_path / "cases.json"
    source.write_text(json.dumps({"label_status": "proposed", "cases": [case]}))
    output = tmp_path / "output.jsonl"
    provider = ScriptedProvider([
        {"status": "uncertain", "issues": []},
        audit("uncertain", draft_span_id="", author_span_id=""),
    ])
    run_suite(source, output, provider)
    row = json.loads(output.read_text())
    assert "error" not in row and row["scores"]["all_labels_match"]
    assert row["report"]["checks"] == []


def test_assessment_requires_three_substantive_reasons():
    from app.application.fidelity import SuggestionAudit

    for field in ("relation_reason", "concern_reason", "revision_reason"):
        with pytest.raises(ValueError):
            SuggestionAudit.model_validate(audit(**{field: "   "}))


def test_acceptance_summary_never_counts_missing_cases_or_abstention_as_success():
    from scripts.accept_fidelity import summarize_run

    cases = [{"id": "positive", "split": "development",
              "expected": {"scan": "issues", "allow_revision": True}},
             {"id": "control", "split": "holdout",
              "expected": {"scan": "clear", "allow_revision": False}}]
    rows = [{"case_id": "positive", "scan": {"status": "uncertain"},
             "scores": {"scan_correct": False, "unsafe_approval": False}}]
    summary = summarize_run(cases, rows)
    assert summary["counts"]["all"]["errors_or_missing"] == 1
    assert not summary["provisional_gates"]["no_unsafe_approval"]
    assert not summary["provisional_gates"]["compatible_label_accuracy_90pct"]
    assert summary["acceptance"] == "failed_provisional_gates"


@pytest.mark.parametrize("revision", ["aligned", "violates"])
def test_audit_discovered_contradiction_does_not_keep_a_clear_banner_or_artistic_scores(revision):
    critic = {
        "passed": True,
        "rubric_scores": dict.fromkeys([
            "story_clarity", "character", "conflict", "emotional_impact",
            "ending", "production_feasibility"], 4),
        "strengths": [], "weaknesses": ["Sai quyền quyết định."],
        "suggestions": ["Giữ kết quả mở."],
    }
    provider = ScriptedProvider([{"status": "clear", "issues": []}, critic, audit(revision=revision)])
    result = review(provider)
    assert result.fidelity["status"] == ("issues" if revision == "aligned" else "unverified")
    assert result.fidelity["checks"][0]["kind"] == "fidelity"
    assert result.passed is None and not result.findings

    if revision == "violates":
        assert result.fidelity["checks"][0]["suggestion"] is None
