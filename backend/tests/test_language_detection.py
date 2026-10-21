import json
import unicodedata

import pytest
from test_generate_workflow import FakeProvider

from app.application.ai_provider import ProviderMetadata
from app.application.language import (
    LanguageSelectionRequired,
    detect_response_language,
    resolve_response_language,
)
from app.application.workflow import create_story_generation_service
from app.core.artifacts import PlanSection


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("A concert pianist waits backstage before her final performance.", "English"),
        ("A character changes her life at a concert.", "English"),
        ("Một người cha muốn xin lỗi con gái trước khi cô đi xa.", "Vietnamese"),
        ("Hành trình học AI và làm lab coach tại VinUni, hướng dẫn các bạn làm bài build phase.", "Vietnamese"),
        ("A young tutor named Nguyễn Minh helps a learner with an AI exercise.", "English"),
        ("The film follows a character named Việt Nam.", "English"),
        ("Việt Nam", None),
        ("Une étudiante apprend à faire confiance à son équipe.", None),
        ("Un film court, une histoire de famille entre un père et son fils.", None),
        ("Hanh trinh hoc AI va huong dan cac ban lam bai tap.", None),
        ("Tôi muốn học. The story is a short film.", None),
        ("AI", None),
        ("lab coach", None),
        ("mẹ", None),
        ("con con con", None),
        ("", None),
        ("123 🎬", None),
        (unicodedata.normalize("NFD", "MỘT NGƯỜI CHA MUỐN GẶP CON GÁI."), "Vietnamese"),
    ],
)
def test_conservative_language_detection(text, expected):
    assert detect_response_language(text) == expected


@pytest.mark.parametrize(("choice", "expected"), [("vi", "Vietnamese"), ("en", "English")])
@pytest.mark.parametrize("qwen_profile", [False, True])
def test_explicit_language_reaches_every_workflow_step_without_changing_the_input(
    choice, expected, qwen_profile
):
    provider = FakeProvider()
    if qwen_profile:
        provider.metadata = ProviderMetadata("ollama", "qwen2.5:3b")
    service = create_story_generation_service(provider)
    idea = "Hanh trinh hoc AI va lam lab coach."
    draft = (PlanSection("ending", "Ending", "", 'lab coach nói "Keep learning." tại VinUni.'),)
    service.analyze(idea, response_language=choice)
    service.plan(idea, (), response_language=choice)
    service.review(idea, "VinUni", "build phase", draft, idea, response_language=choice)
    service.generate(idea, response_language=choice)
    assert len(provider.requests) == 7
    assert provider.fidelity_requests
    for request in provider.fidelity_requests:
        context = json.loads(request.input_text)
        assert context["response_language"] == expected
        assert idea in json.dumps(context["author_context"], ensure_ascii=False)
    for request in provider.requests:
        assert f"Target response language: {expected}" in request.input_text
        assert idea in request.input_text
        if request.stage != "evaluation":
            assert "Keep author terms, names and verbatim source quotations" in request.input_text
            assert "All generated JSON string values must use" not in request.input_text
            assert "Detect the user's input language" not in request.instructions
            assert "All string values must use" not in request.instructions
            assert ("Giữ nguyên thuật" in request.instructions if qwen_profile
                    else "Keep author terms" in request.instructions)
    assert 'lab coach nói \\"Keep learning.\\" tại VinUni.' in provider.requests[3].input_text


def test_uncertain_language_requires_selection_before_any_provider_request():
    provider = FakeProvider()
    service = create_story_generation_service(provider)
    for operation in (
        lambda: service.analyze("AI"),
        lambda: service.plan("AI", ()),
        lambda: service.review("AI", "Title", "Text", (), ""),
        lambda: service.generate("AI"),
    ):
        with pytest.raises(LanguageSelectionRequired, match="chọn ngôn ngữ"):
            operation()
    assert provider.requests == []
    with pytest.raises(ValueError, match="Unsupported"):
        resolve_response_language("Bonjour", "fr")
