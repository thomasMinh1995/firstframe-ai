import json

import pytest
from test_generate_workflow import FakeProvider

from app.application.workflow import create_story_generation_service
from app.core.artifacts import Constraint, PlanSection


@pytest.mark.parametrize(
    ("idea", "language", "policy"),
    [
        (
            "Một lab coach hướng dẫn học viên làm bài build phase tại VinUni.",
            "Vietnamese",
            "Ngôn ngữ góp ý: tiếng Việt",
        ),
        (
            "A young tutor helps a learner finish an AI exercise.",
            "English",
            "Use the explicit target response language for feedback",
        ),
    ],
)
def test_feedback_system_language_covers_generate_plan_and_review_without_editing_author_data(
    idea, language, policy
):
    provider = FakeProvider()
    service = create_story_generation_service(provider)
    constraints = (Constraint(name="ending", value="Giữ kết mở / Keep the ending open"),)
    answers = (("Vai trò?", "lab coach, chưa quyết định kết quả tuyển dụng"),)
    draft_text = 'Người hướng dẫn nói: "Keep learning." Email tại VinUni vẫn chưa mở.'
    sections = (
        PlanSection(section_id="ending", title="Ending", purpose="Final effect", content=draft_text),
    )
    context = json.dumps(
        {"idea": idea, "constraints": [constraints[0].value], "clarifications": answers},
        ensure_ascii=False,
    )

    service.generate(idea, constraints=constraints)
    service.plan(idea, answers=answers, constraints=constraints)
    service.review(idea, "lab coach", "AI tại VinUni", sections, context)

    requests = [r for r in provider.requests if r.stage == "evaluation"]
    assert len(requests) == 3
    for request in requests:
        assert policy in request.instructions
        assert "strengths, weaknesses" in request.instructions
        assert "suggestions" in request.instructions
        assert f"Target response language: {language}" in request.input_text
        assert idea in request.input_text
        assert constraints[0].value in request.input_text
        assert idea not in request.instructions
    # Terms and bilingual quotations stay in the input; no translation/retry rewrites the draft.
    assert len(provider.requests) == 6
    assert "lab coach" in requests[1].input_text
    review = requests[-1]
    assert context in review.input_text
    draft = json.loads(
        review.input_text.split("Current draft (JSON data):\n", 1)[1].split("\n\n", 1)[0]
    )
    assert draft["title"] == "lab coach"
    assert draft["sections"] == [{"title": "Ending", "content": draft_text}]
