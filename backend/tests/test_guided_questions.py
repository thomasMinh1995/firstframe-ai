import pytest
from pydantic import ValidationError

from app.application.workflow import _GuidedReasoningOutput, _render_questions


@pytest.mark.parametrize("options", [[], ["One direction"], ["", "Other"], ["A", "B", "C"]])
def test_question_requires_two_nonempty_directions(options):
    with pytest.raises(ValidationError):
        _GuidedReasoningOutput(summary="A memory.", missing_information=[{
            "question": "Which feeling?", "options": options,
        }])


def test_bare_topics_are_rejected_and_rendered_choices_remain_optional():
    with pytest.raises(ValidationError):
        _GuidedReasoningOutput(summary="A memory.", missing_information=["Family feelings"])
    output = _GuidedReasoningOutput(summary="A memory.", missing_information=[{
        "question": "Bạn muốn nhấn vào điều gì?",
        "options": ["Một cử chỉ nhỏ để tạo sự ấm áp", "Một chút vụng về để tạo tiếng cười"],
    }])
    rendered = _render_questions(output, "Vietnamese")[0]
    assert "Gợi ý tùy chọn" in rendered
    assert "ấm áp" in rendered and "tiếng cười" in rendered
    assert "hướng khác" in rendered and "quyết định sau" in rendered
    assert _render_questions(_GuidedReasoningOutput(summary="Already clear."), "English") == []
