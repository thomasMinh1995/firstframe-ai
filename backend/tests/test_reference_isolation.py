import json

import pytest
from test_generate_workflow import FakeProvider

from app.application.ai_provider import ProviderMetadata
from app.application.example_loader import ExampleLoader
from app.application.knowledge_loader import KnowledgeLoader
from app.application.workflow import create_story_generation_service
from app.core.artifacts import Constraint, PlanSection


@pytest.mark.parametrize("model", ["qwen2.5:3b", "qwen2.5:7b", "other-model"])
def test_story_references_never_enter_runtime_requests(monkeypatch, model):
    def forbidden_examples(*args, **kwargs):
        pytest.fail("Worked stories must not be loaded during generation")

    original_load = KnowledgeLoader.load

    def marked_knowledge(self, name, domain):
        resource = json.loads(json.dumps(original_load(self, name, domain)))
        for entry in resource.get("glossary", resource.get("rules", [])):
            entry["beginner_example"] = "REFERENCE_ONLY_ZEBRA airport daughter"
            entry["future_story_example"] = "REFERENCE_ONLY_ZEBRA"
        return resource

    monkeypatch.setattr(ExampleLoader, "load", forbidden_examples)
    monkeypatch.setattr(KnowledgeLoader, "load", marked_knowledge)
    provider = FakeProvider()
    provider.metadata = ProviderMetadata("ollama", model)
    service = create_story_generation_service(provider)
    service.analyze("Một thợ sửa xe hoàn thành ca làm trong im lặng.", response_language="vi")
    service.plan(
        "Một thợ sửa xe hoàn thành ca làm trong im lặng.",
        (("Âm thanh?", "Không thoại, chỉ tiếng dụng cụ."),),
        constraints=(Constraint(name="location", value="Một tiệm sửa xe"),),
        response_language="vi",
    )
    # The fake generated draft contains a family; only inspect source stages for absence.
    for request in provider.requests[:2]:
        assert "REFERENCE_ONLY_ZEBRA" not in request.input_text
        assert "Reusable domain examples" not in request.input_text
        assert "beginner_example" not in request.input_text
        assert "story_patterns" not in request.input_text
        assert "thợ sửa xe" in request.input_text
    assert "Không thoại, chỉ tiếng dụng cụ." in provider.requests[1].input_text
    for request in provider.requests:
        assert "Current [Middle]: father hides her passport" not in request.instructions
        assert "cha giấu hộ chiếu" not in request.instructions
        assert 'Brief: "Một người cha gặp con gái' not in request.instructions


@pytest.mark.parametrize("language", ["vi", "en"])
def test_author_details_are_not_filtered_from_plan_or_latest_review(language):
    provider = FakeProvider()
    service = create_story_generation_service(provider)
    idea = "Linh, a daughter, says goodbye to her father at the airport with a keychain."
    constraints = (Constraint(name="ending", value="No forgiveness; keep the ending open."),)
    service.plan(idea, (), constraints, response_language=language)
    current = "Linh returns the keychain. She is a lab coach; no hiring result is shown."
    service.review(
        idea, "Linh", "A goodbye",
        (PlanSection(section_id="ending", title="Ending", purpose="End", content=current),),
        json.dumps({"idea": idea, "constraints": [constraints[0].value]}),
        response_language=language,
    )
    for request in provider.requests:
        assert idea in request.input_text
    request = provider.requests[-1]
    assert current in request.input_text
    assert "No forgiveness; keep the ending open." in request.input_text
    assert "father hides her passport" not in request.instructions
    assert "cha giấu hộ chiếu" not in request.instructions
