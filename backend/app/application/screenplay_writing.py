import json
import unicodedata
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from app.api.schemas.projects import ScreenplayProposal
from app.api.schemas.screenplays import SceneWritingResult, ScriptScene, BlockRevisionResult
from app.api.schemas.provenance import TextProvenance
from app.application.ai_provider import MalformedProviderResponseError, StructuredProvider, StructuredRequest
from app.application.language import resolve_response_language
from app.application.screenplay_context import ScreenplayContextTooLarge, check_context_budget
from app.application.progress import progress_step
from app.application.provenance import scene_fields

PROMPT_VERSION = "screenplay-scene-v10"
PROMPT = Path(__file__).resolve().parents[3] / "domains/short-film/prompts/screenplay_scene_prompt.md"


def write_scene(proposal: ScreenplayProposal, provider: StructuredProvider) -> ScreenplayProposal:
    script = proposal.source_screenplay
    target = next(s for s in script.scenes if s.id == proposal.target_scene_id)
    source = next(s for s in script.source_outline.scenes if s.id == target.source_scene_id)
    context = script.source_outline.source
    scoped = proposal.scope == "blocks"
    language = resolve_response_language(context.context.idea, context.response_language)
    position = next(i for i, s in enumerate(script.scenes) if s.id == target.id)
    request = StructuredRequest(
        stage="screenplay_generation", instructions=PROMPT.read_text(encoding="utf-8") + (
            "\nRevise ONLY the selected block IDs. Return replacements with exact expected original kind/text/speaker and a replacement. "
            "Return every selected ID once; never add, remove, reorder blocks or change the heading. Preserve silence and open endings. "
            "Response contract: return only the JSON object with replacements required by the schema; no scene wrapper." if scoped else
            '\nResponse contract: return exactly {"scene":{"heading":"...","blocks":[{"kind":"action","text":"...","speaker":""}]}}. '
            'The scene wrapper is required. A dialogue block is {"kind":"dialogue","text":"spoken words","speaker":"character name"}. '
            'Do not return IDs, a bare scene, a scenes array, markdown or commentary.'),
        input_text=json.dumps({
            "response_language": language,
            "story_plan": context.draft.model_dump(mode="json"),
            "source_scenes": [s.model_dump(mode="json") for s in script.source_outline.scenes],
            "source_scene": source.model_dump(mode="json"), "target_scene_id": target.id,
            "scene_position": {"number": position + 1, "total": len(script.scenes)},
            "source_scene_field_origins": {
                key.removeprefix(f"m2:{source.id}:"): (
                    "author_choice" if origin.is_author_choice else origin.origin)
                for key, value in scene_fields([source]).items() if value.strip()
                for origin in [script.source_outline.provenance.get(key, TextProvenance())]},
            "screenplay_context": [s.model_dump(mode="json") for s in script.scenes],
            "author_request": proposal.instructions,
            **({"revision_scope": "blocks", "block_ids": proposal.block_ids,
                "selected_blocks": [b.model_dump(mode="json") for b in target.blocks if b.id in proposal.block_ids]} if scoped else {}),
            "author_intent": context.context.ai_context(),
        }, ensure_ascii=False), response_model=BlockRevisionResult if scoped else SceneWritingResult)
    check_context_budget(request, provider)
    result = provider.request_structured(request)
    with progress_step("screenplay_validation"):
        try:
            if scoped:
                output = BlockRevisionResult.model_validate(result.output.model_dump())
                by_id = {r.block_id: r for r in output.replacements}
                if len(by_id) != len(output.replacements) or set(by_id) != set(proposal.block_ids):
                    raise ValueError("Replacement IDs differ from selected scope")
                for b in target.blocks:
                    if b.id in by_id and b.model_dump(exclude={"id"}) != by_id[b.id].expected.model_dump():
                        raise ValueError("Expected block text does not match source")
                scene = target.model_copy(deep=True)
                scene.blocks = [b.model_copy(update=by_id[b.id].replacement.model_dump()) if b.id in by_id else b for b in scene.blocks]
                for replacement in output.replacements:
                    b = replacement.replacement
                    if not b.text.strip() or (b.kind == "dialogue" and not b.speaker.strip()) or (b.kind == "action" and b.speaker):
                        raise ValueError("Invalid replacement text/speaker")
                validate_writing_language([r.replacement.model_dump() for r in output.replacements], request.input_text)
                ScriptScene.model_validate(scene.model_dump())
                return proposal.model_copy(update={"scene": scene, "status": "ready", "model": result.model})
            output = SceneWritingResult.model_validate(result.output.model_dump()).scene
            validate_writing_language(output.model_dump(), request.input_text)
        except (ValidationError, ValueError) as error:
            raise MalformedProviderResponseError("Invalid single-scene screenplay", raw_output=result.raw_output) from error
        scene = ScriptScene(id=target.id, source_scene_id=target.source_scene_id, heading=output.heading,
                            blocks=[{**b.model_dump(), "id": str(uuid4())} for b in output.blocks])
        return proposal.model_copy(update={"scene": scene, "status": "ready", "model": result.model})


def validate_writing_language(output, source):
    # Reject script drift; preserve foreign names/quotes already supplied, never rewrite author text.
    def foreign_letters(text):
        return {c for c in unicodedata.normalize("NFC", text)
                if unicodedata.category(c).startswith("L") and "LATIN" not in unicodedata.name(c, "")}
    if foreign_letters(json.dumps(output, ensure_ascii=False)) - foreign_letters(source):
        raise ValueError("Scene introduces a writing script absent from the supplied source.")


def validate_preview(proposal, scene):
    """Enforce the same scope for AI output, author preview and legacy PUT adoption."""
    target = next(s for s in proposal.source_screenplay.scenes if s.id == proposal.target_scene_id)
    if (scene.id, scene.source_scene_id) != (target.id, target.source_scene_id):
        raise ValueError("Giữ đúng ID cảnh nguồn.")
    if proposal.scope == "blocks":
        if scene.heading != target.heading or [b.id for b in scene.blocks] != [b.id for b in target.blocks]:
            raise ValueError("Sửa khối không thay tiêu đề, thêm/bớt hoặc đổi thứ tự khối.")
        if any(b != target.blocks[i] for i,b in enumerate(scene.blocks) if b.id not in proposal.block_ids):
            raise ValueError("Phần ngoài các khối đã chọn phải giữ nguyên.")
