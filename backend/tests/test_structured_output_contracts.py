import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.application.workflow import (
    _EvaluationOutput,
    _PlanningOutput,
    _StructuredStoryPlanOutput,
    Beginning,
    Characters,
    Conflict,
    Ending,
    EvaluationRubricScores,
    Logline,
    Middle,
    ProductionNotes,
    Theme,
    Tone,
    VisualStyle,
    WorkingTitle,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DOMAIN_ROOT = REPO_ROOT / "domains" / "short-film"


def test_output_schema_matches_pydantic_contracts() -> None:
    schema = _load_output_schema()

    assert schema["planning"]["root_fields"] == list(_PlanningOutput.model_fields)
    assert schema["planning"]["story_plan_fields"] == list(_StructuredStoryPlanOutput.model_fields)
    assert schema["planning"]["nested_fields"] == {
        "working_title": list(WorkingTitle.model_fields),
        "logline": list(Logline.model_fields),
        "characters": list(Characters.model_fields),
        "conflict": list(Conflict.model_fields),
        "beginning": list(Beginning.model_fields),
        "middle": list(Middle.model_fields),
        "ending": list(Ending.model_fields),
        "theme": list(Theme.model_fields),
        "visual_style": list(VisualStyle.model_fields),
        "tone": list(Tone.model_fields),
        "production_notes": list(ProductionNotes.model_fields),
    }
    assert schema["evaluation"]["root_fields"] == list(_EvaluationOutput.model_fields)
    assert schema["evaluation"]["rubric_score_fields"] == list(EvaluationRubricScores.model_fields)


def test_story_planner_prompt_mentions_every_planning_schema_field() -> None:
    schema = _load_output_schema()
    prompt = _read_prompt("story_planner_prompt.md")

    for field in schema["planning"]["root_fields"]:
        assert f'"{field}"' in prompt
    for field in schema["planning"]["story_plan_fields"]:
        assert f'"{field}"' in prompt
    for fields in schema["planning"]["nested_fields"].values():
        for field in fields:
            assert f'"{field}"' in prompt


def test_script_critic_prompt_mentions_every_evaluation_schema_field() -> None:
    schema = _load_output_schema()
    prompt = _read_prompt("script_critic_prompt.md")

    for field in schema["evaluation"]["root_fields"]:
        assert f'"{field}"' in prompt
    for field in schema["evaluation"]["rubric_score_fields"]:
        assert f'"{field}"' in prompt


def test_prompts_do_not_request_known_obsolete_fields() -> None:
    prompt_text = (
        _read_prompt("story_planner_prompt.md")
        + "\n"
        + _read_prompt("script_critic_prompt.md")
    )
    obsolete_fields = (
        "core_idea",
        "main_conflict",
        "emotional_goal",
        "ending_direction",
        "key_scenes",
        "evaluation_summary",
        "mentor_questions",
        "overall_read",
        "filmability",
    )

    for field in obsolete_fields:
        assert f'"{field}"' not in prompt_text


def test_evaluation_output_accepts_canonical_contract() -> None:
    output = _EvaluationOutput.model_validate(
        {
            "passed": True,
            "rubric_scores": {
                "story_clarity": 4,
                "character": 4,
                "conflict": 4,
                "emotional_impact": 4,
                "ending": 4,
                "production_feasibility": 4,
            },
            "strengths": ["The emotional stakes are immediate because the goodbye is final."],
            "weaknesses": ["The daughter's objective needs specificity so the conflict is mutual."],
            "suggestions": ["Clarify the departure deadline to sharpen urgency."],
        }
    )

    assert output.rubric_scores.story_clarity == 4


def test_evaluation_output_rejects_obsolete_feedback_contract() -> None:
    with pytest.raises(ValidationError):
        _EvaluationOutput.model_validate(
            {
                "passed": True,
                "rubric_scores": {"clarity": 4, "filmability": 4},
                "strengths": ["Clear emotional stakes."],
                "weaknesses": ["Needs specificity."],
                "suggestions": ["Clarify the deadline."],
                "mentor_questions": ["What does the daughter want?"],
            }
        )


def _load_output_schema() -> dict[str, object]:
    return json.loads((DOMAIN_ROOT / "output_schema.json").read_text(encoding="utf-8"))


def _read_prompt(filename: str) -> str:
    return (DOMAIN_ROOT / "prompts" / filename).read_text(encoding="utf-8")
