"""Regression for the exact synthetic candidate blocked in phase 6 QA-01."""

import json
from pathlib import Path
from uuid import uuid4

import pytest

from app.api.schemas.projects import ProjectResponse, ScreenplayReview
from app.api.schemas.screenplays import SceneReviewResult
from app.application.ai_provider import (
    ProviderMetadata,
    StructuredRequest,
    StructuredResult,
    strict_json_instructions,
)
from app.application.screenplay_context import ScreenplayContextTooLarge, check_context_budget
from app.application.screenplay_review import PROMPT_VERSION, review_scene, review_sources


class CaptureReview:
    metadata = ProviderMetadata("ollama", "qwen2.5:7b", {"num_ctx": 16384})

    def request_structured(self, request):
        self.request = request
        return StructuredResult(SceneReviewResult(notes=[]), "qwen2.5:7b")


def test_phase6_candidate_fits_without_dropping_or_changing_sources():
    fixture = (
        Path(__file__).resolve().parents[2]
        / "docs/evaluations/phase6-qwen7b-2026-10-29/result.json"
    )
    project = ProjectResponse.model_validate(
        json.loads(fixture.read_text())["candidate"]["project"]
    )
    review = ScreenplayReview(
        id=str(uuid4()),
        created_at="2026-10-29T00:00:00Z",
        source_revision=project.revision,
        source_content="frozen QA fixture",
        source_screenplay=project.screenplay,
        source_outline=project.scene_outline,
        target_scene_id=project.screenplay.scenes[0].id,
        prompt_version=PROMPT_VERSION,
    )
    review.sources = review_sources(review)
    before = review.model_dump(mode="json")
    provider = CaptureReview()
    result = review_scene(review, provider)
    assert result.status == "ready"
    assert review.model_dump(mode="json") == before
    request = provider.request
    sent = json.loads(request.input_text)["sources"]
    assert len(sent) == len(review.sources)
    assert [s["text"] for s in sent] == [s.text for s in review.sources]
    assert [s["category"] for s in sent] == [s.category for s in review.sources]
    assert [s["label"] for s in sent] == [s.label for s in review.sources]
    assert (
        len(request.input_text.encode()) + len(strict_json_instructions(request).encode()) <= 11776
    )


@pytest.mark.parametrize(
    "text,num_ctx", [("x" * 12000, 16384), ("Thư chưa mở. " * 1000, 16384), ("small", 4608)]
)
def test_guard_still_rejects_oversized_or_no_room_requests(text, num_ctx):
    provider = CaptureReview()
    provider.metadata = ProviderMetadata("ollama", "qwen2.5:7b", {"num_ctx": num_ctx})
    request = StructuredRequest(
        "Keep all source", text, SceneReviewResult, stage="screenplay_review"
    )
    with pytest.raises(ScreenplayContextTooLarge, match="chưa gửi AI"):
        check_context_budget(request, provider)
    assert not hasattr(provider, "request")
