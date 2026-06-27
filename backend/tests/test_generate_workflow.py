import inspect

from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError

from app.api.routes import generate as generate_route
from app.application.workflow import _PlanningOutput, create_story_generation_service
from app.infrastructure.openai_provider import (
    MissingProviderConfigurationError,
    OpenAIStructuredResult,
    OpenAIStructuredRequest,
    ProviderTimeoutError,
)
from app.main import create_app


class FakeProvider:
    def __init__(self) -> None:
        self.requests: list[OpenAIStructuredRequest] = []

    def request_structured(self, request: OpenAIStructuredRequest) -> OpenAIStructuredResult:
        self.requests.append(request)
        response_model = request.response_model
        if response_model.__name__ == "_ReasoningOutput":
            output = response_model(
                summary="The idea has a clear emotional center.",
                notes=[
                    {
                        "label": "Emotional engine",
                        "content": "A final meeting creates urgent stakes.",
                    }
                ],
                missing_information=[
                    "Why is this the last chance to meet?",
                    "What unresolved truth must be spoken?",
                ],
            )
        elif response_model.__name__ == "_PlanningOutput":
            output = response_model(
                story_plan={
                    "working_title": {"title": "Before She Leaves"},
                    "logline": {
                        "text": (
                            "A retired father tries to reach his daughter before she "
                            "leaves Vietnam."
                        )
                    },
                    "characters": {
                        "protagonist": "Minh, a retired father.",
                        "supporting_characters": ["Linh, his daughter."],
                        "antagonist_or_obstacle": "His fear of losing her.",
                    },
                    "conflict": {
                        "external": "He must reach Linh before her departure.",
                        "internal": "He must choose blessing over control.",
                        "stakes": "This may be their final honest goodbye.",
                    },
                    "beginning": {
                        "setup": "Minh learns Linh is leaving earlier than expected.",
                        "key_event": "He finds a forgotten childhood keychain.",
                    },
                    "middle": {
                        "escalation": "He crosses the city while rehearsing excuses.",
                        "turning_point": "He realizes an apology matters more than stopping her.",
                    },
                    "ending": {
                        "resolution": "He gives Linh his blessing at the airport curb.",
                        "final_image": "His hands release the keychain into hers.",
                    },
                    "theme": {
                        "statement": (
                            "Loving someone can mean releasing them without making them "
                            "carry your fear."
                        )
                    },
                    "visual_style": {
                        "description": "Naturalistic city drama.",
                        "visual_motifs": ["Keys", "Departure boards"],
                    },
                    "tone": {"description": "Tender, restrained, and bittersweet."},
                    "production_notes": {
                        "notes": "Keep the story to a small cast and three locations.",
                        "locations": ["Apartment", "Taxi", "Airport curb"],
                        "cast_size": "Two principals and one day player.",
                    },
                },
            )
        else:
            output = response_model(
                passed=True,
                rubric_scores={
                    "story_clarity": 4,
                    "character": 4,
                    "conflict": 4,
                    "emotional_impact": 4,
                    "ending": 4,
                    "production_feasibility": 4,
                },
                strengths=["The emotional stakes are immediate."],
                weaknesses=["The daughter needs a sharper personal objective."],
                suggestions=["Clarify the exact departure deadline."],
            )
        return OpenAIStructuredResult(output=output, model="fake-model", response_id="fake-response")


class TimeoutService:
    def generate(self, *args: object, **kwargs: object) -> object:
        raise ProviderTimeoutError("timeout")


class MissingConfigService:
    def generate(self, *args: object, **kwargs: object) -> object:
        raise MissingProviderConfigurationError("missing")


def test_planning_output_accepts_single_nested_story_plan_contract() -> None:
    output = _PlanningOutput.model_validate(_valid_story_plan_payload())

    assert output.story_plan.working_title.title == "Before She Leaves"
    assert output.story_plan.logline.text.startswith("A retired father")


def test_planning_output_rejects_obsolete_section_content_contract() -> None:
    with pytest.raises(ValidationError):
        _PlanningOutput.model_validate(
            {
                "sections": [
                    {
                        "title": "Story Plan",
                        "purpose": "Return a structured short-film plan.",
                        "content": _valid_story_plan_payload()["story_plan"],
                    }
                ]
            }
        )


def test_harness_calls_provider_through_runtime_layers() -> None:
    provider = FakeProvider()
    service = create_story_generation_service(provider=provider)  # type: ignore[arg-type]

    run = service.generate(
        "A retired father wants to meet his daughter one last time before she leaves Vietnam."
    )

    assert len(provider.requests) == 3
    assert [request.response_model.__name__ for request in provider.requests] == [
        "_ReasoningOutput",
        "_PlanningOutput",
        "_EvaluationOutput",
    ]
    assert "FirstFrame AI Short Film Story Planner Prompt" in provider.requests[1].instructions
    assert "FirstFrame AI Short Film Script Critic Prompt" in provider.requests[2].instructions
    assert "Short-film domain knowledge" in provider.requests[1].input_text
    assert "film_glossary" in provider.requests[1].input_text
    assert "film_rules" in provider.requests[1].input_text
    assert "story_patterns" in provider.requests[1].input_text
    assert "Reusable domain examples" in provider.requests[1].input_text
    assert "source_id" in provider.requests[1].input_text
    assert "user_idea" in provider.requests[1].input_text
    assert "Short-film story rubric" in provider.requests[2].input_text
    assert "Story Clarity" in provider.requests[2].input_text
    assert "Production Feasibility" in provider.requests[2].input_text
    assert run.analysis.open_questions
    assert run.story_plan.title == "Before She Leaves"
    assert run.story_plan.logline == (
        "A retired father tries to reach his daughter before she leaves Vietnam."
    )
    assert any(section.title == "Main conflict" for section in run.story_plan.sections)
    assert run.evaluation.findings


def test_harness_passes_detected_language_to_all_provider_steps() -> None:
    provider = FakeProvider()
    service = create_story_generation_service(provider=provider)  # type: ignore[arg-type]

    service.generate("Một người cha về hưu muốn gặp con gái trước khi cô rời Việt Nam.")

    assert len(provider.requests) == 3
    assert "Target response language: Vietnamese" in provider.requests[0].input_text
    assert "Target response language: Vietnamese" in provider.requests[1].input_text
    assert "Target response language: Vietnamese" in provider.requests[2].input_text


def test_generate_endpoint_returns_structured_response(monkeypatch) -> None:
    provider = FakeProvider()
    monkeypatch.setattr(
        "app.application.workflow.OpenAIProvider.from_env",
        classmethod(lambda cls: provider),
    )
    client = TestClient(create_app())

    response = client.post(
        "/api/generate",
        json={
            "idea": (
                "A retired father wants to meet his daughter one last time before she "
                "leaves Vietnam."
            )
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["analysis"]["missing_information"]
    assert body["story_plan"]["title"] == "Before She Leaves"
    assert body["story_plan"]["sections"]
    assert body["evaluation"]["rubric_scores"]
    assert body["evaluation"]["findings"]


def test_generate_endpoint_allows_local_frontend_cors_preflight() -> None:
    client = TestClient(create_app())

    for origin in (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ):
        response = client.options(
            "/api/generate",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin
        assert response.headers["access-control-allow-credentials"] == "true"
        assert "POST" in response.headers["access-control-allow-methods"]


def test_generate_endpoint_maps_provider_timeout_safely(monkeypatch) -> None:
    monkeypatch.setattr(
        generate_route,
        "get_story_generation_service",
        lambda: TimeoutService(),
    )
    client = TestClient(create_app())

    response = client.post("/api/generate", json={"idea": "A seed idea."})

    assert response.status_code == 504
    assert response.json() == {"detail": "AI provider timed out."}


def test_generate_endpoint_maps_missing_config_safely(monkeypatch) -> None:
    monkeypatch.setattr(
        generate_route,
        "get_story_generation_service",
        lambda: MissingConfigService(),
    )
    client = TestClient(create_app())

    response = client.post("/api/generate", json={"idea": "A seed idea."})

    assert response.status_code == 503
    assert response.json() == {"detail": "AI provider is not configured."}


def test_generate_controller_does_not_call_openai_directly() -> None:
    source = inspect.getsource(generate_route)

    assert "OpenAI(" not in source
    assert ".responses." not in source


def _valid_story_plan_payload() -> dict[str, object]:
    return {
        "story_plan": {
            "working_title": {"title": "Before She Leaves"},
            "logline": {
                "text": "A retired father tries to reach his daughter before she leaves Vietnam."
            },
            "characters": {
                "protagonist": "Minh, a retired father.",
                "supporting_characters": ["Linh, his daughter."],
                "antagonist_or_obstacle": "His fear of losing her.",
            },
            "conflict": {
                "external": "He must reach Linh before her departure.",
                "internal": "He must choose blessing over control.",
                "stakes": "This may be their final honest goodbye.",
            },
            "beginning": {
                "setup": "Minh learns Linh is leaving earlier than expected.",
                "key_event": "He finds a forgotten childhood keychain.",
            },
            "middle": {
                "escalation": "He crosses the city while rehearsing excuses.",
                "turning_point": "He realizes an apology matters more than stopping her.",
            },
            "ending": {
                "resolution": "He gives Linh his blessing at the airport curb.",
                "final_image": "His hands release the keychain into hers.",
            },
            "theme": {
                "statement": (
                    "Loving someone can mean releasing them without making them carry your fear."
                )
            },
            "visual_style": {
                "description": "Naturalistic city drama.",
                "visual_motifs": ["Keys", "Departure boards"],
            },
            "tone": {"description": "Tender, restrained, and bittersweet."},
            "production_notes": {
                "notes": "Keep the story to a small cast and three locations.",
                "locations": ["Apartment", "Taxi", "Airport curb"],
                "cast_size": "Two principals and one day player.",
            },
        }
    }
