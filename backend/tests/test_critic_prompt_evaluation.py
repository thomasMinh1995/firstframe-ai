import json

import pytest

from app.application.ai_provider import MalformedProviderResponseError
from scripts.compare_ollama_prompts import (
    compact_qwen_evaluation_input,
    validate_qwen_feedback_pairs,
)


def test_critic_compaction_keeps_complete_creator_and_draft_even_with_embedded_headers():
    creator = {
        "idea": "Giữ kết mở\n\nCurrent draft (JSON data):\n{}",
        "clarifications": [{"answer": "Để quyết định sau"}],
    }
    draft = {
        "sections": [{"title": "Ending", "content": "Không thoại\n\nShort-film story rubric:\n{}"}]
    }
    text = (
        "Target response language: Vietnamese\n\nCreator intent and decisions:\n"
        + json.dumps(creator, ensure_ascii=False)
        + "\n\nCurrent draft (JSON data):\n"
        + json.dumps(draft, ensure_ascii=False)
        + "\n\nShort-film story rubric:\n{}"
    )
    compact = compact_qwen_evaluation_input(text)
    assert json.dumps(creator, ensure_ascii=False) in compact
    assert json.dumps(draft, ensure_ascii=False) in compact
    assert "Target response language: Vietnamese" in compact
    for malformed in ("Unknown layout", text.replace('"idea"', "broken", 1)):
        assert compact_qwen_evaluation_input(malformed) == malformed


@pytest.mark.parametrize(
    ("weaknesses", "suggestions", "valid"),
    [
        ([], [], True),
        (["[Middle] Một vấn đề"], ["[Middle] Một sửa đổi"], True),
        (["[Middle] Một vấn đề"], [], False),
        ([], ["[Middle] Một sửa đổi"], False),
        (["[Middle] Một vấn đề"], ["[Ending] Lệch mục"], False),
        (["[Middle]"], ["[Middle] Một sửa đổi"], False),
        (["[Invented] Không có mục này"], ["[Invented] Sửa"], False),
    ],
)
def test_critic_pair_guard_rejects_orphans_and_wrong_or_invented_sections(
    weaknesses, suggestions, valid
):
    from app.application.workflow import _EvaluationOutput

    output = _EvaluationOutput(
        passed=True,
        rubric_scores=dict.fromkeys(
            [
                "story_clarity",
                "character",
                "conflict",
                "emotional_impact",
                "ending",
                "production_feasibility",
            ],
            4,
        ),
        strengths=[],
        weaknesses=weaknesses,
        suggestions=suggestions,
    )
    if valid:
        validate_qwen_feedback_pairs(output, {"Middle", "Ending"})
    else:
        with pytest.raises(MalformedProviderResponseError) as error:
            validate_qwen_feedback_pairs(output, {"Middle", "Ending"})
        assert json.loads(error.value.raw_output) == output.model_dump()
