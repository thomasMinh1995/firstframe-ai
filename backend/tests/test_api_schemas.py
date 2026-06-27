import pytest
from pydantic import ValidationError

from app.api.schemas import IdeaRequest, StoryPlanResponse


def test_idea_request_validates_minimum_payload() -> None:
    request = IdeaRequest(domain_id="any-domain", idea="A quiet mystery at a train station.")

    assert request.domain_id == "any-domain"
    assert request.idea == "A quiet mystery at a train station."
    assert request.constraints == []


def test_idea_request_rejects_empty_idea_before_harness_entry() -> None:
    with pytest.raises(ValidationError):
        IdeaRequest(domain_id="any-domain", idea="")


def test_idea_request_rejects_unknown_transport_fields() -> None:
    with pytest.raises(ValidationError):
        IdeaRequest(domain_id="any-domain", idea="A seed.", provider="openai")


def test_story_plan_response_is_transport_model_not_internal_artifact() -> None:
    response = StoryPlanResponse(request_id="request-1", domain_id="any-domain")

    assert response.sections == []
