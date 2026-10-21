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


@pytest.mark.parametrize("kind", ["open_choice", "creative_proposal"])
def test_optional_choices_are_not_weaknesses_or_blocking_verdicts(kind):
    result = _grounded_evaluation(feedback(passed=False, weaknesses=[{
        "kind": kind, "section": "Ending", "quote": "The result is still unknown.",
        "reason": "Choose the feeling of the final gesture.", "author_quote": "",
        "suggestion": "Try quiet relief or playful warmth, or decide later.",
    }]), draft())
    assert result.passed is True
    assert result.weaknesses == []
    assert len(result.suggestions) == 1
    assert "The result is still unknown." in result.suggestions[0]
    assert "decide later" in result.suggestions[0]


def test_ai_question_cannot_be_used_as_author_evidence():
    from dataclasses import replace

    planning = replace(draft(), creator_context=json.dumps({
        "idea": "Mai helps learners.", "constraints": [], "clarifications": [{
            "question": "Does Mai want to win a prize?", "answer": "Not decided."
        }],
    }))
    with pytest.raises(MalformedProviderResponseError):
        _grounded_evaluation(feedback(weaknesses=[{
            "kind": "contradiction", "section": "Ending", "quote": "The result is still unknown.",
            "reason": "Author wants a prize.", "author_quote": "Mai want to win a prize",
            "suggestion": "Show a prize.",
        }]), planning)


def test_contradiction_requires_evidence_and_still_blocks_when_mixed_with_options():
    issue = {"kind": "contradiction", "section": "Ending", "quote": "The result is still unknown.",
             "reason": "An example contradiction.", "author_quote": "", "suggestion": "Keep facts."}
    with pytest.raises(MalformedProviderResponseError):
        _grounded_evaluation(feedback(weaknesses=[issue]), draft())
    issue["author_quote"] = "Results are unknown."
    option = {**issue, "kind": "creative_proposal", "author_quote": ""}
    result = _grounded_evaluation(feedback(passed=False, weaknesses=[issue, option]), draft())
    assert result.passed is False
    assert len(result.weaknesses) == 1
    assert len(result.suggestions) == 2


def test_older_grounded_record_without_kind_is_not_a_spurious_edit():
    from app.application.dataset_corrections import validate_corrections

    old = feedback(weaknesses=[{
        "section": "Ending", "quote": "The result is still unknown.",
        "reason": "Make this visible.", "author_quote": "", "suggestion": "Show an action.",
    }]).model_dump(exclude_unset=True)
    sample = {"status": "completed", "steps": [{
        "stage": "evaluation", "status": "completed", "output": old,
        "request": {"response_schema": {"title": "_GroundedEvaluationOutput"}},
    }]}
    old["weaknesses"][0].pop("kind", None)
    assert "kind" not in old["weaknesses"][0]
    assert validate_corrections(sample, {"0": old}) == {}


def test_provider_schema_requires_classification_without_suggesting_a_default():
    schema = _GroundedEvaluationOutput.model_json_schema()["$defs"]["_GroundedWeakness"]
    assert "kind" in schema["required"]
    assert "default" not in schema["properties"]["kind"]
