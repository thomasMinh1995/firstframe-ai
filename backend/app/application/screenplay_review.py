import json
from pathlib import Path
from time import monotonic
from uuid import uuid4

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model

from app.api.schemas.projects import ScreenplayReview
from app.api.schemas.screenplays import ReviewSource, SavedReviewNote
from app.api.schemas.provenance import TextProvenance
from app.application.ai_provider import (
    MalformedProviderResponseError,
    ProviderTimeoutError,
    StructuredProvider,
    StructuredRequest,
)
from app.application.language import resolve_response_language
from app.application.progress import progress_step
from app.application.screenplay_context import check_context_budget

PROMPT_VERSION = "screenplay-review-v7-evidence-selection"
PROMPT = (
    Path(__file__).resolve().parents[3] / "domains/short-film/prompts/screenplay_review_prompt.md"
)


class ReviewComment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_id: str
    observation: str = Field(min_length=1, max_length=2000)
    impact: str = Field(min_length=1, max_length=2000)
    suggestion: str = Field(default="", max_length=2000)


class ChoiceCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    observation: str = Field(min_length=1, max_length=2000)
    relation: Literal["compatible", "conflict", "unresolved"]
    author_choice_id: str
    impact: str = Field(default="", max_length=2000)
    suggestion: str = Field(default="", max_length=2000)


class CraftConcern(ReviewComment):
    kind: Literal["craft", "uncertain"]


def selection_model(target_texts, author_ids):
    # A required check per target excerpt prevents selecting only a compliant passage.
    check = create_model(
        "ChoiceCheck",
        __base__=ChoiceCheck,
        author_choice_id=(Literal[tuple(["", *author_ids])], ...),
    )
    craft = create_model(
        "CraftConcern", __base__=CraftConcern, target_id=(Literal[tuple(target_texts)], ...)
    )
    checks = create_model(
        "TargetChecks",
        __config__=ConfigDict(extra="forbid"),
        **{
            a: (check, Field(description="Target text (immutable data): " + text))
            for a, text in target_texts.items()
        },
    )
    return create_model(
        "SceneReviewSelection",
        __config__=ConfigDict(extra="forbid"),
        checks=(checks, ...),
        craft_notes=(list[craft], Field(default_factory=list, max_length=6)),
        question=(str, Field(default="", max_length=2000)),
    )


def remaining_review_time(deadline):
    remaining = deadline - monotonic()
    if remaining <= 0:
        raise ProviderTimeoutError("Screenplay review exceeded its 60-second budget.")
    return remaining


def review_sources(review: ScreenplayReview) -> list[ReviewSource]:
    script = review.source_screenplay
    index = next(i for i, s in enumerate(script.scenes) if s.id == review.target_scene_id)
    target = script.scenes[index]
    sources = []
    def add(id, label, text, category, field="context", scene_id=None, block_id=None, provenance=None):
        if text.strip():
            provenance = provenance or TextProvenance()
            if category == "author_choice" and not provenance.is_author_choice:
                category = "context"
            sources.append(ReviewSource(id=id, label=label, text=text, category=category, field=field,
                                        scene_id=scene_id, block_id=block_id, provenance=provenance))
    for s in script.scenes[max(0, index - 1):index + 2]:
        key = f"script:{s.id}:heading"
        add(key, s.heading or "Tiêu đề cảnh", s.heading, "screenplay", "heading", s.id,
            provenance=script.provenance.get(key))
        for i, block in enumerate(s.blocks):
            label = f"{s.heading or 'Cảnh'} · khối {i + 1}"
            for field in ("text", "speaker"):
                key = f"block:{block.id}:{field}"
                add(key, label if field == "text" else label + " · người nói", getattr(block, field),
                    "screenplay", field, s.id, block.id, script.provenance.get(key))
    outline = script.source_outline
    scene = next(s for s in outline.scenes if s.id == target.source_scene_id)
    def choice(key, label, text):
        id = f"m2:{scene.id}:{key}"
        add(id, label, text, "author_choice", "choice", provenance=outline.provenance.get(id))
    choice("action", "Diễn tiến dàn cảnh đã chọn", scene.action)
    for key, label in (("location", "Địa điểm"), ("time", "Thời điểm"), ("characters", "Nhân vật"), ("goal", "Mục tiêu"), ("purpose", "Đóng góp")):
        choice(key, label, getattr(scene, key))
    choice("keep_or_avoid", "Điều muốn giữ/tránh", scene.keep_or_avoid)
    choice("viewer_intent", "Cảm nhận người xem", scene.viewer_intent)
    for key, text in scene.staging_choices.items():
        choice(f"staging:{key}", "Lựa chọn dàn cảnh: " + key, text)
    context, draft = outline.source.context, outline.source.draft
    author = TextProvenance(origin="author_input")
    add("intent:idea", "Ý tưởng tác giả", context.idea, "author_choice", "choice", provenance=author)
    for i, text in enumerate(context.constraints):
        add(f"intent:constraint:{i}", f"Giới hạn {i + 1}", text, "author_choice", "choice", provenance=author)
    for i, answer in enumerate(context.clarifications):
        add(f"intent:answer:{i}", answer.question, answer.answer, "author_choice", "choice", provenance=author)
    add("plan:logline", "Logline nguồn", draft.logline, "context",
        provenance=outline.source.draft_provenance.get("logline"))
    for i, section in enumerate(draft.sections):
        add(f"plan:section:{i}", section.title, section.content, "context",
            provenance=outline.source.draft_provenance.get(f"section:{i}:content"))
    return sources


def review_scene(review: ScreenplayReview, provider: StructuredProvider) -> ScreenplayReview:
    deadline = monotonic() + 60
    context = review.source_screenplay.source_outline.source
    # Short IDs belong only to this request; durable references keep their original IDs.
    sources = {}
    model_sources = []
    counters = {"screenplay": 0, "author_choice": 0}
    prefixes = {"screenplay": "S", "author_choice": "A"}
    blocks = {b.id: b for s in review.source_screenplay.scenes for b in s.blocks}
    quotes = {}
    for source in review.sources:
        if source.category == "context":
            continue  # Unconfirmed plan/AI proposals cannot establish an author requirement.
        # Excerpts retain every character of the scoped screenplay/author sources.
        for offset in range(0, len(source.text), 1000):
            text = source.text[offset : offset + 1000]
            counters[source.category] += 1
            alias = f"{prefixes[source.category]}{counters[source.category]}"
            sources[alias] = source
            quotes[alias] = text
            block = blocks.get(source.block_id)
            model_sources.append(
                {
                    "id": alias,
                    "label": source.label,
                    "text": text,
                    "category": source.category,
                    "field": source.field,
                    "is_target": source.category == "screenplay"
                    and source.scene_id == review.target_scene_id,
                    "block_kind": block.kind if block else None,
                }
            )
    language = resolve_response_language(context.context.idea, context.response_language)
    instructions = (
        PROMPT.read_text(encoding="utf-8")
        + f"\nOutput language: {language}. Write every observation, impact, suggestion and question in {language}."
    )
    request = StructuredRequest(
        stage="screenplay_review",
        instructions=instructions,
        input_text=json.dumps(
            {
                "response_language": language,
                "author_request": review.instructions,
                "sources": model_sources,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        response_model=selection_model(
            {s["id"]: s["text"] for s in model_sources if s["is_target"] and s["field"] == "text"},
            [s["id"] for s in model_sources if s["category"] == "author_choice"],
        ),
        timeout_seconds=remaining_review_time(deadline),
    )
    check_context_budget(request, provider)
    with progress_step("screenplay_review"):
        result = provider.request_structured(request)
    remaining_review_time(deadline)
    with progress_step("screenplay_review_validation"):
        try:
            output = request.response_model.model_validate(result.output.model_dump())
            comments = []
            for alias in type(output.checks).model_fields:
                check = getattr(output.checks, alias)
                if check.relation == "conflict":
                    if not check.author_choice_id:
                        raise ValueError("Intent mismatch needs author choice evidence")
                    comments.append(("intent_mismatch", check, [alias, check.author_choice_id]))
            if not comments:
                comments.extend((n.kind, n, [n.target_id]) for n in output.craft_notes)
            # Keep the public six-note limit; full checks remain in recorded provider output.
            comments = comments[:6]
            notes = []
            for kind, note, aliases in comments:
                if not note.observation.strip() or not note.impact.strip():
                    raise ValueError("Empty review observation/impact")
                refs = [sources[a] for a in aliases]
                if not any(
                    s.category == "screenplay"
                    and s.scene_id == review.target_scene_id
                    and s.field == "text"
                    for s in refs
                ):
                    raise ValueError("Missing evidence from target screenplay text")
                if kind == "intent_mismatch" and not any(
                    s.category == "author_choice" for s in refs
                ):
                    raise ValueError("Intent mismatch needs author choice evidence")
                if any(not quotes[a].strip() or quotes[a] not in sources[a].text for a in aliases):
                    raise ValueError("Review evidence does not match snapshot")
                notes.append(
                    SavedReviewNote(
                        id=str(uuid4()),
                        kind=kind,
                        observation=note.observation,
                        impact=note.impact,
                        suggestion=note.suggestion,
                        evidence=[
                            {"source_id": sources[a].id, "quote": quotes[a]} for a in aliases
                        ],
                    )
                )
        except (ValueError, ValidationError) as error:
            raise MalformedProviderResponseError(
                "Invalid screenplay review evidence", raw_output=result.raw_output
            ) from error
    return review.model_copy(update={"status": "ready", "notes": notes, "question": output.question, "model": result.model})
