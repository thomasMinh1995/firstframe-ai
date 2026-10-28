import json
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from app.api.schemas.projects import ScreenplayReview
from app.api.schemas.screenplays import ReviewSource, SavedReviewNote, SceneReviewResult
from app.application.ai_provider import MalformedProviderResponseError, StructuredProvider, StructuredRequest
from app.application.language import resolve_response_language
from app.application.progress import progress_step
from app.application.screenplay_context import check_context_budget

PROMPT_VERSION = "screenplay-review-v3-constraint-first"
PROMPT = Path(__file__).resolve().parents[3] / "domains/short-film/prompts/screenplay_review_prompt.md"


def review_sources(review: ScreenplayReview) -> list[ReviewSource]:
    script = review.source_screenplay
    index = next(i for i, s in enumerate(script.scenes) if s.id == review.target_scene_id)
    target = script.scenes[index]
    sources = []
    def add(id, label, text, category, field="context", scene_id=None, block_id=None):
        if text.strip():
            sources.append(ReviewSource(id=id, label=label, text=text, category=category, field=field,
                                        scene_id=scene_id, block_id=block_id))
    for s in script.scenes[max(0, index - 1):index + 2]:
        add(f"script:{s.id}:heading", s.heading or "Tiêu đề cảnh", s.heading, "screenplay", "heading", s.id)
        for i, block in enumerate(s.blocks):
            label = f"{s.heading or 'Cảnh'} · khối {i + 1}"
            add(f"block:{block.id}:text", label, block.text, "screenplay", "text", s.id, block.id)
            add(f"block:{block.id}:speaker", label + " · người nói", block.speaker, "screenplay", "speaker", s.id, block.id)
    outline = script.source_outline
    scene = next(s for s in outline.scenes if s.id == target.source_scene_id)
    add(f"m2:{scene.id}:action", "Diễn tiến M2 đã chọn", scene.action, "author_choice", "choice")
    for key, label in (("location", "Địa điểm"), ("time", "Thời điểm"), ("characters", "Nhân vật"), ("goal", "Mục tiêu"), ("purpose", "Đóng góp")):
        add(f"m2:{scene.id}:{key}", label, getattr(scene, key), "author_choice", "choice")
    add(f"m2:{scene.id}:keep_or_avoid", "Điều muốn giữ/tránh", scene.keep_or_avoid, "author_choice", "choice")
    add(f"m2:{scene.id}:viewer_intent", "Cảm nhận người xem", scene.viewer_intent, "author_choice", "choice")
    for key, text in scene.staging_choices.items():
        add(f"m2:{scene.id}:staging:{key}", "Lựa chọn dàn cảnh: " + key, text, "author_choice", "choice")
    context, draft = outline.source.context, outline.source.draft
    add("intent:idea", "Ý tưởng tác giả", context.idea, "author_choice", "choice")
    for i, text in enumerate(context.constraints):
        add(f"intent:constraint:{i}", f"Giới hạn {i + 1}", text, "author_choice", "choice")
    for i, answer in enumerate(context.clarifications):
        add(f"intent:answer:{i}", answer.question, answer.answer, "author_choice", "choice")
    add("plan:logline", "Logline nguồn", draft.logline, "context")
    for i, section in enumerate(draft.sections):
        add(f"plan:section:{i}", section.title, section.content, "context")
    return sources


def review_scene(review: ScreenplayReview, provider: StructuredProvider) -> ScreenplayReview:
    context = review.source_screenplay.source_outline.source
    # Short IDs belong only to this request; durable references keep their original IDs.
    sources = {}
    model_sources = []
    counters = {"screenplay": 0, "author_choice": 0, "context": 0}
    prefixes = {"screenplay": "S", "author_choice": "A", "context": "C"}
    blocks = {b.id: b for s in review.source_screenplay.scenes for b in s.blocks}
    for source in review.sources:
        counters[source.category] += 1
        alias = f"{prefixes[source.category]}{counters[source.category]}"
        sources[alias] = source
        block = blocks.get(source.block_id)
        model_sources.append({"id": alias, "label": source.label, "text": source.text,
            "category": source.category, "field": source.field,
            "is_target": source.category == "screenplay" and source.scene_id == review.target_scene_id,
            "block_kind": block.kind if block else None})
    request = StructuredRequest(stage="screenplay_review", instructions=PROMPT.read_text(encoding="utf-8"),
        input_text=json.dumps({"response_language": resolve_response_language(context.context.idea, context.response_language),
            "author_request": review.instructions, "sources": model_sources}, ensure_ascii=False),
        response_model=SceneReviewResult)
    check_context_budget(request, provider)
    with progress_step("screenplay_review"):
        result = provider.request_structured(request)
    with progress_step("screenplay_review_validation"):
        try:
            output = SceneReviewResult.model_validate(result.output.model_dump())
            for note in output.notes:
                if not note.observation.strip() or not note.impact.strip():
                    raise ValueError("Empty review observation/impact")
                refs = []
                for evidence in note.evidence:
                    source = sources.get(evidence.source_id)
                    if source is None or not evidence.quote.strip() or evidence.quote not in source.text:
                        raise ValueError("Review evidence does not match snapshot")
                    refs.append(source)
                    evidence.source_id = source.id
                if not any(s.category == "screenplay" and s.scene_id == review.target_scene_id and s.field == "text" for s in refs):
                    raise ValueError("Missing evidence from target screenplay text")
                if note.kind == "intent_mismatch" and not any(s.category == "author_choice" for s in refs):
                    raise ValueError("Intent mismatch needs author choice evidence")
            notes = [SavedReviewNote(id=str(uuid4()), **n.model_dump()) for n in output.notes]
        except (ValueError, ValidationError) as error:
            raise MalformedProviderResponseError("Invalid screenplay review evidence", raw_output=result.raw_output) from error
    return review.model_copy(update={"status": "ready", "notes": notes, "question": output.question, "model": result.model})
