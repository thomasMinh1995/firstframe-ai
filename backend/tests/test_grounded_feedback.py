import json

import pytest
from pydantic import ValidationError

from app.application.ai_provider import MalformedProviderResponseError
from app.application.workflow import (
    _grounded_evaluation,
    _GroundedEvaluationOutput,
    _LLMPlanningArtifact,
)
from app.core.artifacts import ArtifactMetadata, PlanSection


def draft():
    return _LLMPlanningArtifact(
        metadata=ArtifactMetadata("p", "short-film", "planning"), source_reasoning_id="r",
        title="Workshop", logline="Mai guides beginners.",
        sections=(PlanSection("end", "Ending", "", "The result is still unknown."),),
        creator_context=json.dumps({"idea": 'Mai says "keep learning".\nResults are unknown.'}),
    )


def feedback(**changes):
    return _GroundedEvaluationOutput.model_validate({
        "strengths": [{"section": "Ending", "quote": "The result is still unknown.",
                       "reason": "Leaves the external result open."}],
        "weaknesses": [],
        "rubric_scores": dict.fromkeys(["story_clarity", "character", "conflict",
                                        "emotional_impact", "ending", "production_feasibility"], 4),
        "passed": True, **changes,
    })


def test_current_quote_and_mixed_terms_are_preserved():
    output = _grounded_evaluation(feedback(weaknesses=[{
        "section": "logline", "quote": "Mai guides beginners.",
        "author_quote": 'Mai says "keep learning".', "reason": "Specify the teaching action.",
        "suggestion": "Keep workshop terminology and show the action.",
    }]), draft())
    assert output.strengths == ['[Ending] “The result is still unknown.” — Leaves the external result open.']
    assert output.suggestions == ['[logline] Keep workshop terminology and show the action.']


@pytest.mark.parametrize("section,quote", [
    ("Ending", "An obsolete draft won a prize."),
    ("Unknown section", "The result is still unknown."),
    ("Ending", "Mai guides beginners."),
])
def test_rejects_old_invented_or_wrong_section_quote(section, quote):
    with pytest.raises(MalformedProviderResponseError):
        _grounded_evaluation(feedback(strengths=[{
            "section": section, "quote": quote, "reason": "Specific reason.",
        }]), draft())


def test_rejects_invented_creator_evidence():
    with pytest.raises(MalformedProviderResponseError):
        _grounded_evaluation(feedback(weaknesses=[{
            "section": "Ending", "quote": "The result is still unknown.",
            "reason": "Contradicts author.", "author_quote": "Mai won a prize.",
            "suggestion": "Disclose the prize.",
        }]), draft())


def test_generic_strings_or_empty_reasons_are_not_valid_feedback():
    for strengths in [["Great story!"], [{"section": "Ending", "quote": "result", "reason": " "}]]:
        with pytest.raises(ValidationError):
            feedback(strengths=strengths)


def test_historical_editorial_feedback_still_uses_string_contract():
    from app.application.dataset_corrections import validate_corrections
    from app.application.workflow import _EvaluationOutput

    legacy = {
        "passed": True, "rubric_scores": feedback().rubric_scores.model_dump(),
        "strengths": ["Historical praise"], "weaknesses": [], "suggestions": [],
    }
    sample = {"status": "completed", "steps": [{
        "stage": "evaluation", "status": "completed", "output": legacy,
        "request": {"response_schema": _EvaluationOutput.model_json_schema()},
    }]}
    edited = {**legacy, "strengths": ["Human editorial correction"]}
    assert validate_corrections(sample, {"0": edited}) == {"0": edited}
