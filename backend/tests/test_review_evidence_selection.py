"""Source selection is a transport guarantee, not a semantic quality verdict."""

import json
from pathlib import Path
from uuid import uuid4

import pytest

from app.api.schemas.projects import ProjectResponse, ScreenplayReview
from app.application.ai_provider import (
    MalformedProviderResponseError,
    ProviderMetadata,
    StructuredResult,
)
from app.application.screenplay_review import PROMPT_VERSION, review_scene, review_sources
from test_screenplay_review import UncheckedSelection
from test_projects import project_client  # noqa: F401


def source_review():
    fixture = (
        Path(__file__).resolve().parents[2]
        / "docs/evaluations/phase6-qwen7b-2026-10-29/result.json"
    )
    p = ProjectResponse.model_validate(json.loads(fixture.read_text())["candidate"]["project"])
    r = ScreenplayReview(
        id=str(uuid4()),
        created_at="2026-10-29T00:00:00Z",
        source_revision=p.revision,
        source_content="frozen fixture",
        source_screenplay=p.screenplay,
        source_outline=p.scene_outline,
        target_scene_id=p.screenplay.scenes[0].id,
        prompt_version=PROMPT_VERSION,
    )
    r.sources = review_sources(r)
    return r


class SelectionProvider:
    metadata = ProviderMetadata("ollama", "qwen2.5:7b", {"num_ctx": 16384})

    def __init__(self, mutate=lambda *args: None):
        self.mutate = mutate
        self.requests = []

    def request_structured(self, request):
        self.requests.append(request)
        sources = json.loads(request.input_text)["sources"]
        self.output = {
            "checks": {
                s["id"]: {
                    "author_choice_id": "",
                    "observation": "Hai nguồn có thể cùng đúng.",
                    "relation": "compatible",
                    "impact": "",
                }
                for s in sources
                if s["is_target"] and s["field"] == "text"
            },
            "craft_notes": [],
            "question": "",
        }
        self.mutate(self.output, sources, request)
        return StructuredResult(
            UncheckedSelection(**self.output), "qwen2.5:7b", raw_output=json.dumps(self.output)
        )


def conflict(output, sources, request):
    author = next(s["id"] for s in sources if s["category"] == "author_choice")
    next(iter(output["checks"].values())).update(
        relation="conflict",
        author_choice_id=author,
        observation="Giả lập mâu thuẫn có nguồn.",
        impact="Tác động giả lập.",
    )


def test_canonical_quotes_are_extracted_and_raw_provider_result_is_unchanged():
    r = source_review()
    before = r.model_dump(mode="json")
    provider = SelectionProvider(conflict)
    result = review_scene(r, provider)
    note = result.notes[0]
    catalog = {s.id: s for s in r.sources}
    assert len(note.evidence) == 2
    assert all(e.quote == catalog[e.source_id].text for e in note.evidence)
    assert catalog[note.evidence[0].source_id].field == "text"
    assert catalog[note.evidence[1].source_id].category == "author_choice"
    assert "evidence" not in next(iter(provider.output["checks"].values()))
    assert r.model_dump(mode="json") == before
    # A deliberately unsupported interpretation still passes source validation;
    # this must never be reported as a semantic correctness certificate.
    assert note.observation == "Giả lập mâu thuẫn có nguồn."


@pytest.mark.parametrize(
    "mode",
    [
        "unknown_target",
        "heading_target",
        "author_target",
        "missing_check",
        "unknown_check",
        "unknown_author",
        "missing_author",
        "blank_conflict",
        "old_quote_output",
        "background_craft",
    ],
)
def test_untrusted_selection_is_rejected_without_changing_the_snapshot(mode):
    r = source_review()
    before = r.model_dump(mode="json")

    def mutate(output, sources, request):
        key = next(iter(output["checks"]))
        if mode == "unknown_target":
            output["checks"]["S999"] = output["checks"].pop(key)
        elif mode == "heading_target":
            output["checks"][next(s["id"] for s in sources if s["field"] == "heading")] = output[
                "checks"
            ].pop(key)
        elif mode == "author_target":
            output["checks"][next(s["id"] for s in sources if s["category"] == "author_choice")] = (
                output["checks"].pop(key)
            )
        elif mode == "missing_check":
            del output["checks"][key]
        elif mode == "unknown_check":
            output["checks"]["C999"] = output["checks"][key]
        elif mode == "unknown_author":
            conflict(output, sources, request)
            output["checks"][key]["author_choice_id"] = "A999"
        elif mode == "missing_author":
            output["checks"][key].update(relation="conflict", impact="Tác động giả lập.")
        elif mode == "blank_conflict":
            conflict(output, sources, request)
            output["checks"][key]["impact"] = " "
        elif mode == "old_quote_output":
            output.clear()
            output["notes"] = []
        elif mode == "background_craft":
            output["craft_notes"] = [
                {
                    "target_id": "C1",
                    "kind": "craft",
                    "observation": "Không hợp lệ.",
                    "impact": "Không hợp lệ.",
                }
            ]

    provider = SelectionProvider(mutate)
    with pytest.raises(MalformedProviderResponseError):
        review_scene(r, provider)
    assert len(provider.requests) == 1
    assert r.model_dump(mode="json") == before


def test_long_target_is_split_into_exact_bounded_excerpts_without_losing_text():
    r = source_review()
    r.source_screenplay.scenes[0].blocks[0].text = "a" * 1000 + "\nPhần cuối giữ nguyên."
    r.sources = review_sources(r)
    block_id = r.source_screenplay.scenes[0].blocks[0].id

    def choose_tail(output, sources, request):
        conflict(output, sources, request)
        tail = next(s["id"] for s in sources if s["text"] == "\nPhần cuối giữ nguyên.")
        first = next(iter(output["checks"].values()))
        author = first["author_choice_id"]
        first.update(relation="compatible", author_choice_id="")
        output["checks"][tail].update(
            relation="conflict",
            author_choice_id=author,
            observation="Phần cuối có vấn đề giả lập.",
            impact="Tác động giả lập.",
        )

    provider = SelectionProvider(choose_tail)
    result = review_scene(r, provider)
    sent = json.loads(provider.requests[0].input_text)["sources"]
    excerpts = [
        s["text"]
        for s in sent
        if s["is_target"] and s["field"] == "text" and s["label"] == sent[1]["label"]
    ]
    assert "".join(excerpts) == r.source_screenplay.scenes[0].blocks[0].text
    evidence = result.notes[0].evidence[0]
    assert evidence.source_id == f"block:{block_id}:text"
    assert evidence.quote == "\nPhần cuối giữ nguyên."
    assert len(evidence.quote) <= 1000


def test_unconfirmed_background_is_preserved_in_snapshot_but_not_a_rule():
    r = source_review()
    before = r.model_dump(mode="json")
    provider = SelectionProvider()
    result = review_scene(r, provider)
    sent = json.loads(provider.requests[0].input_text)["sources"]
    assert any(s.category == "context" for s in r.sources)
    assert not any(s["category"] == "context" for s in sent)
    assert [s["text"] for s in sent if s["category"] == "author_choice"] == [
        s.text for s in r.sources if s.category == "author_choice"
    ]
    schema = provider.requests[0].response_model.model_json_schema()
    checks = schema["$defs"]["TargetChecks"]
    assert set(checks["required"]) == {
        s["id"] for s in sent if s["is_target"] and s["field"] == "text"
    }
    assert all(
        s["text"] in checks["properties"][s["id"]]["description"]
        for s in sent
        if s["is_target"] and s["field"] == "text"
    )
    assert r.model_dump(mode="json") == before and result.notes == []


def test_conflict_takes_priority_over_secondary_craft_notes():
    r = source_review()

    def secondary(output, sources, request):
        conflict(output, sources, request)
        target = next(iter(output["checks"]))
        output["craft_notes"] = [
            {
                "kind": "craft",
                "target_id": target,
                "observation": "Góp ý phụ.",
                "impact": "Tác động phụ.",
            }
        ]

    result = review_scene(r, SelectionProvider(secondary))
    assert [n.kind for n in result.notes] == ["intent_mismatch"]


EVIDENCE = Path(__file__).resolve().parents[2] / "docs/evaluations/qa01-qwen-evidence-2026-10-29"


@pytest.mark.parametrize("run,index", [(run, i) for run in ("run-1", "run-2") for i in range(8)])
def test_replay_frozen_qwen_outputs_keeps_exact_contract(run, index):
    calls = json.loads((EVIDENCE / run / "calls.json").read_text())
    rows = json.loads((EVIDENCE / run / "results.json").read_text())
    row, call = rows[index], calls[index]
    r = ScreenplayReview.model_validate(row["review"])
    before = r.model_dump(mode="json")

    class Replay:
        metadata = ProviderMetadata("ollama", "qwen2.5:7b", {"num_ctx": 16384})

        def request_structured(self, request):
            assert json.loads(request.input_text) == call["input"]
            assert request.instructions == call["instructions"]
            assert request.response_model.model_json_schema() == call["response_schema"]
            raw = call["response"]["message"]["content"]
            return StructuredResult(
                request.response_model.model_validate_json(raw), "qwen2.5:7b", raw_output=raw
            )

    result = review_scene(r, Replay())
    # These retained responses include semantic errors; the separate live gate evaluates quality.
    assert result.status == "ready"
    assert any(n.kind == "intent_mismatch" for n in result.notes) == row["expected_conflict"]
    assert [n.model_dump(exclude={"id", "assessment"}) for n in result.notes] == [
        n.model_dump(exclude={"id", "assessment"}) for n in r.notes
    ]
    assert r.model_dump(mode="json") == before


def test_previous_v6_reviews_reopen_without_rewriting_or_calling_ai(project_client, monkeypatch):
    from app.api.routes import projects, screenplay_reviews

    old_root = EVIDENCE.parent / "qa01-review-context-qwen7b-final-2026-10-29"
    old = json.loads((old_root / "results.json").read_text())[6]["review"]
    base = json.loads((EVIDENCE.parent / "phase6-qwen7b-2026-10-29/result.json").read_text())[
        "candidate"
    ]["project"]
    p = ProjectResponse.model_validate(base)
    p.id = str(uuid4())
    p.screenplay_reviews = [ScreenplayReview.model_validate(old)]
    projects.get_project_store().create(p.model_dump(mode="json", exclude_computed_fields=True))

    def forbidden():
        raise AssertionError("Opening legacy review must not call AI")

    monkeypatch.setattr(screenplay_reviews, "get_review_provider", forbidden)
    response = project_client[0].get(f"/api/projects/{p.id}")
    assert response.status_code == 200
    assert response.json()["screenplay_reviews"] == [old]


def test_more_than_six_conflicts_keep_bounded_notes_and_all_recorded_checks():
    r = source_review()
    template = r.source_screenplay.scenes[0].blocks[0]
    r.source_screenplay.scenes[0].blocks = [
        template.model_copy(update={"id": str(uuid4()), "text": f"Hành động {i}."})
        for i in range(7)
    ]
    r.sources = review_sources(r)

    def all_conflicts(output, sources, request):
        author = next(s["id"] for s in sources if s["category"] == "author_choice")
        for check in output["checks"].values():
            check.update(
                relation="conflict",
                author_choice_id=author,
                observation="Vấn đề giả lập.",
                impact="Tác động giả lập.",
            )

    provider = SelectionProvider(all_conflicts)
    result = review_scene(r, provider)
    assert len(result.notes) == 6 and len(provider.output["checks"]) == 7
    assert len(r.source_screenplay.scenes[0].blocks) == 7 and r.notes == []


def test_expired_review_discards_late_output_and_never_retries(monkeypatch):
    from app.application import screenplay_review as module
    from app.application.ai_provider import ProviderTimeoutError

    values = iter([0, 0, 61])
    monkeypatch.setattr(module, "monotonic", lambda: next(values))
    review = source_review()
    before = review.model_dump(mode="json")
    provider = SelectionProvider(conflict)
    with pytest.raises(ProviderTimeoutError):
        review_scene(review, provider)
    assert len(provider.requests) == 1 and review.model_dump(mode="json") == before
