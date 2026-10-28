import json
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from app.api.schemas.projects import SceneProposal
from app.api.schemas.scenes import StagingIdea, StagingResult, StagingSource
from app.application.ai_provider import MalformedProviderResponseError, StructuredProvider, StructuredRequest
from app.application.language import resolve_response_language
from app.application.progress import progress_step

PROMPT_VERSION = "scene-staging-v1"
PROMPT = Path(__file__).resolve().parents[3] / "domains/short-film/prompts/scene_staging_prompt.md"


def staging_sources(proposal: SceneProposal) -> list[StagingSource]:
    outline = proposal.source_outline
    index = next(i for i, s in enumerate(outline.scenes) if s.id == proposal.target_scene_id)
    selected = outline.scenes[index]
    sources = []
    def add(key, label, text):
        if text.strip():
            sources.append(StagingSource(id=key, label=label, text=text))
    labels = {"title": "Tên cảnh", "action": "Diễn tiến", "location": "Địa điểm", "time": "Thời điểm",
              "characters": "Nhân vật", "goal": "Nhân vật muốn gì", "purpose": "Mục đích cảnh",
              "viewer_intent": "Cảm nhận người xem", "keep_or_avoid": "Điều muốn giữ/tránh"}
    for key, text in selected.model_dump(exclude={"id", "staging_choices"}).items():
        add(f"scene:{selected.id}:{key}", labels[key], text)
    for key, text in selected.staging_choices.items():
        add(f"scene:{selected.id}:staging:{key}", "Phương án dàn cảnh đang giữ", text)
    for neighbor in outline.scenes[max(0, index - 1):index + 2]:
        if neighbor.id != selected.id:
            add(f"scene:{neighbor.id}:action", f"Cảnh liền kề: {neighbor.title}", neighbor.action)
    context, draft = outline.source.context, outline.source.draft
    add("intent:idea", "Ý tưởng tác giả", context.idea)
    for i, text in enumerate(context.constraints):
        add(f"intent:constraint:{i}", f"Giới hạn {i + 1}", text)
    for i, answer in enumerate(context.clarifications):
        add(f"intent:answer:{i}", answer.question, answer.answer)
    add("plan:logline", "Logline nguồn", draft.logline)
    for i, section in enumerate(draft.sections):
        add(f"plan:section:{i}", section.title, section.content)
    return sources


def suggest_staging(proposal: SceneProposal, provider: StructuredProvider) -> SceneProposal:
    sources = staging_sources(proposal)
    context = proposal.source_outline.source.context
    result = provider.request_structured(StructuredRequest(
        stage="staging_generation", instructions=PROMPT.read_text(encoding="utf-8"),
        input_text=json.dumps({
            "response_language": resolve_response_language(context.idea, proposal.source_outline.source.response_language),
            "target_scene_id": proposal.target_scene_id, "author_request": proposal.instructions,
            "sources": [s.model_dump() for s in sources],
        }, ensure_ascii=False), response_model=StagingResult,
    ))
    with progress_step("staging_validation"):
        try:
            output = StagingResult.model_validate(result.output.model_dump())
            texts = {s.id: s.text for s in sources}
            for idea in output.ideas:
                if not all(text.strip() for text in (idea.reason, idea.suggestion, idea.purpose)):
                    raise ValueError("Empty staging suggestion")
                if not any(e.source_id.startswith(f"scene:{proposal.target_scene_id}:") for e in idea.evidence):
                    raise ValueError("Missing evidence from selected scene")
                if any(e.source_id not in texts or not e.quote.strip() or e.quote not in texts[e.source_id]
                       for e in idea.evidence):
                    raise ValueError("Staging quote does not match source")
            ideas = [StagingIdea(id=str(uuid4()), **i.model_dump()) for i in output.ideas]
        except (ValueError, ValidationError) as error:
            raise MalformedProviderResponseError("Invalid staging evidence or suggestion", raw_output=result.raw_output) from error
    return proposal.model_copy(update={"status": "ready", "staging_ideas": ideas,
        "staging_sources": sources, "staging_question": output.question, "model": result.model,
        "prompt_version": PROMPT_VERSION})
