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
        "verdict": verdict,
        "reason": "Giữ việc hướng dẫn và kết quả chưa biết.",
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
    assert check["verification_note"]
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
        {"verdict": "contradicted"},
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
