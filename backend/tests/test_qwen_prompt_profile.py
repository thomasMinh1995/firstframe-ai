import hashlib
from pathlib import Path

import pytest
from test_generate_workflow import FakeProvider

from app.application.ai_provider import ProviderMetadata, strict_json_instructions
from app.application.dataset import capture_workflow, get_dataset_store
from app.application.workflow import (
    compact_qwen_planning_input,
    create_story_generation_service,
)
from app.core.artifacts import Constraint


@pytest.mark.parametrize(
    ("provider_name", "model", "profile"),
    [
        ("ollama", "qwen2.5:3b", True),
        ("ollama", "other-model", False),
        ("openai", "qwen2.5:3b", False),
    ],
)
def test_prompt_profile_keeps_context_schema_and_recorded_effective_prompt(
    provider_name, model, profile
):
    provider = FakeProvider()
    provider.metadata = ProviderMetadata(provider_name, model)
    brief = "Mẹ chờ trong bếp; không thoại, giữ kết mở."
    with capture_workflow("generate", {"idea": brief}) as recording:
        service = create_story_generation_service(provider)
        service.generate(brief, constraints=(Constraint(name="location", value="Một căn bếp"),))
        recording.complete({"idea": brief})
    record = get_dataset_store().records()[0]
    root = Path(__file__).resolve().parents[2] / "domains/short-film/prompts"
    if profile:
        root /= "ollama-qwen2.5-3b"
    for request, step, name in zip(
        provider.requests,
        record["steps"],
        ("story_mentor", "story_planner", "script_critic"),
        strict=True,
    ):
        expected_root = root.parent if profile and request.stage == "evaluation" else root
        assert request.instructions == (expected_root / f"{name}_prompt.md").read_text().strip()
        assert "Target response language: Vietnamese" in request.input_text
        assert "Một căn bếp" in request.input_text
        assert step["request"]["effective_instructions"] == strict_json_instructions(request)
        assert step["request"]["response_schema"] == request.response_model.model_json_schema()
        if request.stage == "planning":
            assert ("Reusable domain examples:" in request.input_text) is not profile
            assert ("Short-film domain knowledge:" in request.input_text) is not profile
        if request.stage == "evaluation":
            assert "Short-film story rubric:" in request.input_text
            assert "Current draft (JSON data):" in request.input_text
        assert (
            step["request"]["prompt_sha256"]
            == hashlib.sha256(strict_json_instructions(request).encode()).hexdigest()
        )


def test_qwen_profile_keeps_creator_answers_and_current_revision_context():
    provider = FakeProvider()
    provider.metadata = ProviderMetadata("ollama", "qwen2.5:3b")
    service = create_story_generation_service(provider)
    service.plan(
        "Người cha muốn xin lỗi con gái, không ngăn con đi.",
        answers=(("Kết thúc?", "Để quyết định sau"),),
        constraints=(Constraint(name="location", value="Chỉ một căn hộ"),),
    )
    for request in provider.requests:
        assert "không ngăn con đi" in request.input_text
        assert "Để quyết định sau" in request.input_text
        assert "Chỉ một căn hộ" in request.input_text


def test_compaction_preserves_author_decisions_and_notes_verbatim_and_handles_unknown_layout():
    creator = (
        '{"idea":"Không tiết lộ người vắng mặt","clarifications":[{"answer":"Để quyết định sau"}]}'
    )
    header = "Target response language: Vietnamese"
    prefix = header + "\n\nCreator intent and decisions:\n" + creator
    planning = prefix + "\n\nReasoning notes:\nGiữ kết mở."
    assert (
        compact_qwen_planning_input(planning + "\n\nShort-film domain knowledge:\nlarge references")
        == planning
    )
    assert (
        compact_qwen_planning_input("Unknown layout; keep all author data")
        == "Unknown layout; keep all author data"
    )
