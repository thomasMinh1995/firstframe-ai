"""Grounded relation transport and controlled presentation; no live model calls."""

import json
from pathlib import Path
from uuid import uuid4

import pytest
from test_projects import project_client  # noqa: F401
from test_screenplay_review import UncheckedSelection
from app.api.schemas.projects import ProjectResponse, ScreenplayReview
from app.application.ai_provider import (
    MalformedProviderResponseError,
    ProviderMetadata,
    StructuredResult,
)
from app.application.screenplay_review import (
    PROMPT_VERSION,
    PRESENTATION,
    review_scene,
    review_sources,
)

ROOT = Path(__file__).resolve().parents[2] / "docs/evaluations"
EVIDENCE = ROOT / "qa01-qwen-review-v8-2026-10-29"


def source_review(violating=False):
    p = ProjectResponse.model_validate(
        json.loads((ROOT / "phase6-qwen7b-2026-10-29/result.json").read_text())["candidate"][
            "project"
        ]
    )
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
    if violating:
        for b in r.source_screenplay.scenes[0].blocks:
            b.text = "Con gái mở lá thư."
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
        self.output = {"craft_issue": "none"}
        self.mutate(self.output, sources, request)
        return StructuredResult(
            UncheckedSelection(**self.output), "qwen2.5:7b", raw_output=json.dumps(self.output)
        )


def test_canonical_quotes_and_localized_flags_never_rewrite_snapshot_or_raw_output():
    r = source_review(True)
    before = r.model_dump(mode="json")
    provider = SelectionProvider()
    result = review_scene(r, provider)
    catalog = {s.id: s for s in r.sources}
    for note in result.notes:
        assert len(note.evidence) == 2
        assert all(e.quote == catalog[e.source_id].text for e in note.evidence)
        assert catalog[note.evidence[0].source_id].field == "text"
        assert catalog[note.evidence[1].source_id].category == "author_choice"
        assert (note.observation, note.impact) == PRESENTATION["Vietnamese"]["conflict"]
        assert note.suggestion == ""
    assert set(provider.output) == {"craft_issue"} and result.question == ""
    assert r.model_dump(mode="json") == before
    # The model supplies only a style code; literal checks do not certify overall story quality.
    assert len(provider.requests) == len(r.source_screenplay.scenes[0].blocks)


@pytest.mark.parametrize(
    "mode",
    ["legacy_relation", "generated_prose", "old_quote_output", "invalid_issue", "target_override"],
)
def test_untrusted_output_is_rejected_without_relocation_retry_or_snapshot_change(mode):
    r = source_review()
    before = r.model_dump(mode="json")

    def mutate(output, sources, request):
        if mode == "legacy_relation":
            output["relations"] = {"A999": "conflict"}
        elif mode == "generated_prose":
            output["impact"] = "Vi phạm giới hạn 99. Wrong interpretation."
        elif mode == "old_quote_output":
            output["notes"] = []
        elif mode == "invalid_issue":
            output["craft_issue"] = "invented"
        elif mode == "target_override":
            output["target_id"] = "S999"

    provider = SelectionProvider(mutate)
    with pytest.raises(MalformedProviderResponseError):
        review_scene(r, provider)
    assert len(provider.requests) == 1 and r.model_dump(mode="json") == before


def test_long_target_excerpts_retain_every_character_and_bind_the_tail_exactly():
    r = source_review()
    block = r.source_screenplay.scenes[0].blocks[0]
    block.text = "a" * 1000 + "\nCon gái mở lá thư."
    r.sources = review_sources(r)

    provider = SelectionProvider()
    result = review_scene(r, provider)
    excerpts = [
        s["text"]
        for req in provider.requests
        for s in json.loads(req.input_text)["sources"]
        if s["category"] == "screenplay" and s["label"] == r.sources[1].label
    ]
    assert "".join(excerpts) == block.text
    assert result.notes[0].evidence[0].source_id == f"block:{block.id}:text"
    assert result.notes[0].evidence[0].quote == "\nCon gái mở lá thư."


def test_style_request_contains_only_target_while_full_author_snapshot_is_preserved():
    r = source_review()
    before = r.model_dump(mode="json")
    provider = SelectionProvider()
    result = review_scene(r, provider)
    assert any(s.category == "context" for s in r.sources)
    for request in provider.requests:
        sent = json.loads(request.input_text)["sources"]
        target = [s for s in sent if s["category"] == "screenplay"]
        assert len(target) == 1 and target[0]["is_target"] and target[0]["field"] == "text"
        assert [s["text"] for s in sent if s["category"] == "author_choice"] == []
        assert not any(s["category"] == "context" for s in sent)
    assert r.model_dump(mode="json") == before and result.notes == []
    assert all(0 < req.timeout_seconds <= 60 for req in provider.requests)
    assert provider.requests[-1].timeout_seconds < provider.requests[0].timeout_seconds


def test_conflicts_take_priority_over_other_excerpt_craft_flags():
    r = source_review(True)
    result = review_scene(r, SelectionProvider(lambda o, s, q: o.update(craft_issue="reference")))
    assert len(result.notes) == 3 and all(n.kind == "intent_mismatch" for n in result.notes)


@pytest.mark.parametrize("choice,language", [("vi", "Vietnamese"), ("en", "English")])
def test_public_prose_is_controlled_and_uses_selected_language(choice, language):
    r = source_review(True)
    r.source_screenplay.source_outline.source.response_language = choice
    result = review_scene(r, SelectionProvider())
    assert all(
        (n.observation, n.impact) == PRESENTATION[language]["conflict"] and n.suggestion == ""
        for n in result.notes
    )
    assert result.question == ""


@pytest.mark.parametrize("issue", ["action_clarity", "reference", "continuity", "dialogue"])
def test_craft_labels_are_localized_without_model_authored_prose(issue):
    r = source_review()
    if issue == "dialogue":
        for b in r.source_screenplay.scenes[0].blocks:
            b.kind = "dialogue"
            b.speaker = "Con gái"
        r.sources = review_sources(r)
    result = review_scene(r, SelectionProvider(lambda o, s, q: o.update(craft_issue=issue)))
    assert all(
        (n.observation, n.impact) == PRESENTATION["Vietnamese"][issue]
        and n.kind == "craft"
        and n.suggestion == ""
        for n in result.notes
    )


@pytest.mark.parametrize(
    "folder", ["qa01-review-context-qwen7b-final-2026-10-29", "qa01-qwen-evidence-2026-10-29/run-2"]
)
def test_v6_v7_saved_reviews_reopen_without_rewriting_or_calling_ai(
    project_client, monkeypatch, folder
):
    from app.api.routes import projects, screenplay_reviews

    old = json.loads((ROOT / folder / "results.json").read_text())[6]["review"]
    p = ProjectResponse.model_validate(
        json.loads((ROOT / "phase6-qwen7b-2026-10-29/result.json").read_text())["candidate"][
            "project"
        ]
    )
    p.id = str(uuid4())
    p.screenplay_reviews = [ScreenplayReview.model_validate(old)]
    projects.get_project_store().create(p.model_dump(mode="json", exclude_computed_fields=True))

    def forbidden():
        raise AssertionError("Opening old reviews must not call AI")

    monkeypatch.setattr(screenplay_reviews, "get_review_provider", forbidden)
    response = project_client[0].get(f"/api/projects/{p.id}")
    assert response.status_code == 200 and response.json()["screenplay_reviews"] == [old]


def test_seven_target_checks_keep_six_public_notes_without_skipping_any_excerpt():
    r = source_review()
    b = r.source_screenplay.scenes[0].blocks[0]
    r.source_screenplay.scenes[0].blocks = [
        b.model_copy(update={"id": str(uuid4()), "text": f"Con gái mở lá thư, hành động {i}."})
        for i in range(7)
    ]
    r.sources = review_sources(r)
    provider = SelectionProvider()
    result = review_scene(r, provider)
    assert len(result.notes) == 6 and len(provider.requests) == 7 and r.notes == []


def test_expired_review_discards_late_result_and_never_retries(monkeypatch):
    from app.application import screenplay_review as module
    from app.application.ai_provider import ProviderTimeoutError

    values = iter([0, 0, 61])
    monkeypatch.setattr(module, "monotonic", lambda: next(values))
    r = source_review(True)
    before = r.model_dump(mode="json")
    provider = SelectionProvider()
    with pytest.raises(ProviderTimeoutError):
        review_scene(r, provider)
    assert len(provider.requests) == 1 and r.model_dump(mode="json") == before


def test_action_mislabeled_as_dialogue_never_becomes_a_craft_note():
    r = source_review()
    result = review_scene(r, SelectionProvider(lambda o, s, q: o.update(craft_issue="dialogue")))
    assert result.status == "ready" and result.notes == []


def test_whitespace_only_excerpt_is_preserved_but_never_becomes_an_ai_note():
    r = source_review()
    r.source_screenplay.scenes[0].blocks = r.source_screenplay.scenes[0].blocks[:1]
    r.source_screenplay.scenes[0].blocks[0].text = " " * 1000 + "Con gái mở lá thư."
    r.sources = review_sources(r)
    before = r.model_dump(mode="json")
    provider = SelectionProvider()
    result = review_scene(r, provider)
    assert len(provider.requests) == 1 and len(result.notes) == 1
    assert result.notes[0].evidence[0].quote == "Con gái mở lá thư."
    assert r.model_dump(mode="json") == before


def test_deadline_also_covers_local_validation(monkeypatch):
    from app.application import screenplay_review as module
    from app.application.ai_provider import ProviderTimeoutError

    values = iter([0, 0, 0, 61])
    monkeypatch.setattr(module, "monotonic", lambda: next(values))
    r = source_review()
    r.source_screenplay.scenes[0].blocks = r.source_screenplay.scenes[0].blocks[:1]
    r.sources = review_sources(r)
    before = r.model_dump(mode="json")
    provider = SelectionProvider()
    with pytest.raises(ProviderTimeoutError):
        review_scene(r, provider)
    assert len(provider.requests) == 1 and r.model_dump(mode="json") == before


@pytest.mark.parametrize("run,index", [(run, i) for run in ("run-1", "run-2") for i in range(10)])
def test_final_live_qwen_replay_passes_source_pair_and_presentation_gates(run, index):
    from scripts.check_review_context import evaluate_review

    rows = json.loads((EVIDENCE / run / "results.json").read_text())
    all_calls = json.loads((EVIDENCE / run / "calls.json").read_text())
    row = rows[index]
    calls = [c for c in all_calls if c["case"] == row["case"]]
    r = ScreenplayReview.model_validate(row["review"])
    before = r.model_dump(mode="json")

    class Replay:
        metadata = ProviderMetadata("ollama", "qwen2.5:7b", {"num_ctx": 16384})
        index = 0

        def request_structured(self, request):
            call = calls[self.index]
            self.index += 1
            assert json.loads(request.input_text) == call["input"]
            assert request.instructions == call["instructions"]
            assert request.response_model.model_json_schema() == call["response_schema"]
            raw = call["response"]["message"]["content"]
            return StructuredResult(
                request.response_model.model_validate_json(raw), "qwen2.5:7b", raw_output=raw
            )

    provider = Replay()
    result = review_scene(r, provider)
    expected = json.loads((EVIDENCE / "expectations.json").read_text())[row["case"]]
    verdict = evaluate_review(result.model_dump(mode="json"), expected)
    assert (
        all(v for k, v in verdict.items() if k != "unexpected_cjk")
        and not verdict["unexpected_cjk"]
    )
    assert provider.index == len(calls) and r.model_dump(mode="json") == before
    assert [n.model_dump(exclude={"id", "assessment"}) for n in result.notes] == [
        n.model_dump(exclude={"id", "assessment"}) for n in r.notes
    ]
