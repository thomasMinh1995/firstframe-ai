import json
from pathlib import Path
from time import monotonic
from uuid import uuid4

from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

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
from app.application.review_opposition import literal_opposition

PROMPT_VERSION = "screenplay-review-v8-block-relations"
PROMPT = (
    Path(__file__).resolve().parents[3] / "domains/short-film/prompts/screenplay_review_prompt.md"
)


ISSUES = Literal["none", "action_clarity", "reference", "continuity", "dialogue"]


class BlockCraftReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    craft_issue: ISSUES


PRESENTATION = {
    "Vietnamese": {
        "conflict": (
            "Chi tiết này có thể mâu thuẫn với lựa chọn tác giả được dẫn bên dưới.",
            "Giữ chi tiết này có thể làm thay đổi lựa chọn tác giả đã xác nhận; bạn quyết định giữ hay yêu cầu sửa.",
        ),
        "action_clarity": (
            "Hành động trong đoạn này có thể cần diễn đạt rõ hơn.",
            "Người đọc có thể khó hình dung hành động để dàn dựng.",
        ),
        "reference": (
            "Tham chiếu trong đoạn này có thể chưa rõ.",
            "Người đọc có thể không xác định được người hoặc vật đang được nhắc tới.",
        ),
        "continuity": (
            "Các chi tiết trong đoạn này có thể cần đối chiếu về sự liền mạch.",
            "Trình tự hoặc trạng thái trong đoạn có thể khiến người đọc hiểu không nhất quán.",
        ),
        "dialogue": (
            "Lời thoại này có thể cần đọc lại thành tiếng.",
            "Nhịp hoặc cách nói có thể làm câu thoại khó diễn tự nhiên.",
        ),
    },
    "English": {
        "conflict": (
            "This detail may conflict with the author choice cited below.",
            "Keeping this detail may change the confirmed author choice; you decide whether to keep it or request a revision.",
        ),
        "action_clarity": (
            "The action in this passage may need clearer wording.",
            "A reader may have difficulty picturing the action for staging.",
        ),
        "reference": (
            "A reference in this passage may be unclear.",
            "A reader may have difficulty identifying the person or object being referenced.",
        ),
        "continuity": (
            "The details in this passage may need a continuity check.",
            "The order or state of details may lead to an inconsistent reading.",
        ),
        "dialogue": (
            "This dialogue may benefit from being read aloud.",
            "The rhythm or delivery may make this line difficult to perform naturally.",
        ),
    },
}


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

    def add(
        id, label, text, category, field="context", scene_id=None, block_id=None, provenance=None
    ):
        if text.strip():
            provenance = provenance or TextProvenance()
            if category == "author_choice" and not provenance.is_author_choice:
                category = "context"
            sources.append(
                ReviewSource(
                    id=id,
                    label=label,
                    text=text,
                    category=category,
                    field=field,
                    scene_id=scene_id,
                    block_id=block_id,
                    provenance=provenance,
                )
            )

    for s in script.scenes[max(0, index - 1) : index + 2]:
        key = f"script:{s.id}:heading"
        add(
            key,
            s.heading or "Tiêu đề cảnh",
            s.heading,
            "screenplay",
            "heading",
            s.id,
            provenance=script.provenance.get(key),
        )
        for i, block in enumerate(s.blocks):
            label = f"{s.heading or 'Cảnh'} · khối {i + 1}"
            for field in ("text", "speaker"):
                key = f"block:{block.id}:{field}"
                add(
                    key,
                    label if field == "text" else label + " · người nói",
                    getattr(block, field),
                    "screenplay",
                    field,
                    s.id,
                    block.id,
                    script.provenance.get(key),
                )
    outline = script.source_outline
    scene = next(s for s in outline.scenes if s.id == target.source_scene_id)

    def choice(key, label, text):
        id = f"m2:{scene.id}:{key}"
        add(id, label, text, "author_choice", "choice", provenance=outline.provenance.get(id))

    choice("action", "Diễn tiến dàn cảnh đã chọn", scene.action)
    for key, label in (
        ("location", "Địa điểm"),
        ("time", "Thời điểm"),
        ("characters", "Nhân vật"),
        ("goal", "Mục tiêu"),
        ("purpose", "Đóng góp"),
    ):
        choice(key, label, getattr(scene, key))
    choice("keep_or_avoid", "Điều muốn giữ/tránh", scene.keep_or_avoid)
    choice("viewer_intent", "Cảm nhận người xem", scene.viewer_intent)
    for key, text in scene.staging_choices.items():
        choice(f"staging:{key}", "Lựa chọn dàn cảnh: " + key, text)
    context, draft = outline.source.context, outline.source.draft
    author = TextProvenance(origin="author_input")
    add(
        "intent:idea", "Ý tưởng tác giả", context.idea, "author_choice", "choice", provenance=author
    )
    for i, text in enumerate(context.constraints):
        add(
            f"intent:constraint:{i}",
            f"Giới hạn {i + 1}",
            text,
            "author_choice",
            "choice",
            provenance=author,
        )
    for i, answer in enumerate(context.clarifications):
        add(
            f"intent:answer:{i}",
            answer.question,
            answer.answer,
            "author_choice",
            "choice",
            provenance=author,
        )
    add(
        "plan:logline",
        "Logline nguồn",
        draft.logline,
        "context",
        provenance=outline.source.draft_provenance.get("logline"),
    )
    for i, section in enumerate(draft.sections):
        add(
            f"plan:section:{i}",
            section.title,
            section.content,
            "context",
            provenance=outline.source.draft_provenance.get(f"section:{i}:content"),
        )
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
    instructions = PROMPT.read_text(encoding="utf-8")
    authors = {a: quotes[a] for a, s in sources.items() if s.category == "author_choice"}
    targets = [
        s for s in model_sources if s["is_target"] and s["field"] == "text" and s["text"].strip()
    ]
    model = BlockCraftReview
    # Check the whole scoped source before fan-out; large projects must not start partial AI work.
    aggregate = StructuredRequest(
        instructions,
        json.dumps({"sources": model_sources}, ensure_ascii=False, separators=(",", ":")),
        model,
        stage="screenplay_review",
    )
    check_context_budget(aggregate, provider)
    target_scene = next(
        s for s in review.source_screenplay.scenes if s.id == review.target_scene_id
    )
    source_scene = next(
        s
        for s in review.source_screenplay.source_outline.scenes
        if s.id == target_scene.source_scene_id
    )
    conflicts, craft = [], []
    actual_model = None
    for target in targets:
        block = blocks[sources[target["id"]].block_id]
        data = {
            "response_language": language,
            "author_request": review.instructions,
            "sources": [{**target, "speaker": block.speaker}],
        }
        request = StructuredRequest(
            instructions,
            json.dumps(data, ensure_ascii=False, separators=(",", ":")),
            model,
            stage="screenplay_review",
            timeout_seconds=remaining_review_time(deadline),
        )
        check_context_budget(request, provider)
        with progress_step("screenplay_review"):
            result = provider.request_structured(request)
        remaining_review_time(deadline)
        with progress_step("screenplay_review_validation"):
            try:
                output = model.model_validate(result.output.model_dump())
                candidates = [
                    a
                    for a in authors
                    if literal_opposition(quotes[a], target["text"], block, source_scene.characters)
                ]
                if candidates:
                    author = min(
                        candidates, key=lambda a: not sources[a].id.startswith("intent:constraint:")
                    )
                    conflicts.append(("intent_mismatch", "conflict", [target["id"], author]))
                elif output.craft_issue != "none":
                    if output.craft_issue != "dialogue" or block.kind == "dialogue":
                        craft.append(("craft", output.craft_issue, [target["id"]]))
                actual_model = result.model
            except (ValueError, ValidationError) as error:
                raise MalformedProviderResponseError(
                    "Invalid screenplay review relation", raw_output=result.raw_output
                ) from error
    notes = []
    # Stable localized labels describe flags; generated prose cannot invent facts, numbering or fixes.
    for kind, issue, aliases in (conflicts or craft)[:6]:
        if any(not quotes[a].strip() or quotes[a] not in sources[a].text for a in aliases):
            raise MalformedProviderResponseError("Review evidence does not match snapshot")
        observation, impact = PRESENTATION[language][issue]
        notes.append(
            SavedReviewNote(
                id=str(uuid4()),
                kind=kind,
                observation=observation,
                impact=impact,
                suggestion="",
                evidence=[{"source_id": sources[a].id, "quote": quotes[a]} for a in aliases],
            )
        )
    remaining_review_time(deadline)
    return review.model_copy(
        update={"status": "ready", "notes": notes, "question": "", "model": actual_model}
    )
