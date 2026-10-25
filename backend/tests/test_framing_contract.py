"""Offline contract checks only; these do not grade a model's story interpretation."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from scripts.framing_contract import FramingAssessment, PROMPT_PATH, validate_sources


def assessment():
    return {
        "themes": [
            {"topic_id": "R1", "stance": "unclear", "evidence": []},
            {"topic_id": "R2", "stance": "not_applicable", "evidence": []},
            {"topic_id": "R3", "stance": "not_applicable", "evidence": []},
        ],
        "language": {"status": "no_violation", "evidence": []},
    }


def test_unclear_without_evidence_is_valid_and_does_not_mutate_input():
    data = assessment()
    before = deepcopy(data)
    parsed = FramingAssessment.model_validate(data)
    validate_sources(parsed, {})
    assert parsed.model_dump() == data == before


@pytest.mark.parametrize("stance", ["critical", "endorsing"])
def test_certain_stance_requires_evidence_without_automatic_fallback(stance):
    data = assessment()
    data["themes"][0]["stance"] = stance
    with pytest.raises(ValidationError, match="requires evidence"):
        FramingAssessment.model_validate(data)
    assert data["themes"][0]["stance"] == stance


@pytest.mark.parametrize("stance", ["critical", "endorsing", "unclear"])
def test_source_validation_checks_anchors_not_stance_meaning(stance):
    data = assessment()
    data["themes"][0].update(
        stance=stance, evidence=[{"card_id": "ending", "quote": "Phim phản đối hành vi này."}]
    )
    # Even an opposite stance passes source checks: semantics must be graded separately.
    validate_sources(FramingAssessment.model_validate(data),
                     {"ending": "Lời dẫn: Phim phản đối hành vi này."})


def test_language_violation_stays_independent_of_critical_stance():
    data = assessment()
    data["themes"][0].update(
        stance="critical", evidence=[{"card_id": "ending", "quote": "Phim phản đối."}]
    )
    data["language"]["status"] = "clear_violation"
    with pytest.raises(ValidationError, match="clear_violation requires evidence"):
        FramingAssessment.model_validate(data)
    data["language"]["evidence"] = [{"card_id": "speech", "quote": "Từ bị cấm."}]
    parsed = FramingAssessment.model_validate(data)
    validate_sources(parsed, {"ending": "Phim phản đối.", "speech": "Từ bị cấm."})
    assert parsed.language.status == "clear_violation"


@pytest.mark.parametrize("status", ["uncertain", "no_violation"])
def test_language_can_have_no_evidence_without_a_clear_violation(status):
    data = assessment()
    data["language"]["status"] = status
    validate_sources(FramingAssessment.model_validate(data), {})


def test_duplicate_topic_cannot_replace_a_missing_topic():
    data = assessment()
    data["themes"][1]["topic_id"] = "R1"
    with pytest.raises(ValidationError, match="Exactly one"):
        FramingAssessment.model_validate(data)


def test_topic_order_does_not_matter():
    data = assessment()
    data["themes"].reverse()
    assert FramingAssessment.model_validate(data).model_dump() == data


@pytest.mark.parametrize("field", ["behavior_evidence", "viewpoint_evidence", "suggestion"])
def test_old_split_fields_and_creative_edits_are_not_in_contract(field):
    data = assessment()
    data["themes"][0][field] = []
    with pytest.raises(ValidationError, match="Extra inputs"):
        FramingAssessment.model_validate(data)


def test_publish_decision_is_not_a_model_output_field():
    data = assessment()
    data["publish_recommendation"] = "block"
    with pytest.raises(ValidationError, match="Extra inputs"):
        FramingAssessment.model_validate(data)


@pytest.mark.parametrize("card_id,quote", [
    ("unknown", "Một câu."),
    ("first", "Câu thuộc card khác."),
    ("first", "Một  câu."),
    ("first", "   "),
])
def test_invalid_source_is_not_relocated_or_normalized(card_id, quote):
    data = assessment()
    data["themes"][0]["evidence"] = [{"card_id": card_id, "quote": quote}]
    cards = {"first": "Một câu.", "second": "Câu thuộc card khác."}
    before = deepcopy((data, cards))
    with pytest.raises(ValueError):
        validate_sources(FramingAssessment.model_validate(data), cards)
    assert (data, cards) == before


def test_two_distinct_excerpts_from_one_card_are_not_duplicate_evidence():
    data = assessment()
    data["themes"][0]["evidence"] = [
        {"card_id": "ending", "quote": "Cô phản đối."},
        {"card_id": "ending", "quote": "Phim bác bỏ việc ép buộc."},
    ]
    cards = {"ending": "Cô phản đối. Phim bác bỏ việc ép buộc."}
    validate_sources(FramingAssessment.model_validate(data), cards)
    data["themes"][0]["evidence"].append(deepcopy(data["themes"][0]["evidence"][0]))
    with pytest.raises(ValueError, match="Duplicate evidence"):
        validate_sources(FramingAssessment.model_validate(data), cards)


def test_not_applicable_does_not_force_evidence_but_checks_any_returned_quote():
    data = assessment()
    data["themes"][1]["evidence"] = [{"card_id": "workshop", "quote": "Chỉ có chiếc máy."}]
    validate_sources(FramingAssessment.model_validate(data), {"workshop": "Chỉ có chiếc máy."})
    with pytest.raises(ValueError, match="unknown card"):
        validate_sources(FramingAssessment.model_validate(data), {})


def test_exported_schema_and_prompt_are_available_to_an_offline_runner():
    schema = FramingAssessment.model_json_schema()
    assert set(schema["required"]) == {"themes", "language"}
    assert schema["additionalProperties"] is False
    theme = schema["$defs"]["ThemeAssessment"]
    assert set(theme["properties"]) == {"topic_id", "stance", "evidence"}
    assert PROMPT_PATH.is_file()
