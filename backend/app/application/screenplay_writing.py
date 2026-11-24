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
from app.application.screenplay_context import (
    UNANSWERED_QUESTIONS_RULE, ScreenplayContextTooLarge, check_context_budget,
)
from app.application.progress import progress_step
from app.application.provenance import scene_fields
from app.application.screenplay_composition import (
    can_compose, cast_names, composition_request, preserve_continuation_actions, render_composition,
    speaker_addresses, speaker_voices,
)

PROMPT_VERSION = "screenplay-scene-v28-vietnamese-dialogue"
PROMPT = Path(__file__).resolve().parents[3] / "domains/short-film/prompts/screenplay_scene_prompt.md"


def write_scene(proposal: ScreenplayProposal, provider: StructuredProvider) -> ScreenplayProposal:
    script = proposal.source_screenplay
    target = next(s for s in script.scenes if s.id == proposal.target_scene_id)
    source = next(s for s in script.source_outline.scenes if s.id == target.source_scene_id)
    context = script.source_outline.source
    scoped = proposal.scope == "blocks"
    language = resolve_response_language(context.context.idea, context.response_language)
    position = next(i for i, s in enumerate(script.scenes) if s.id == target.id)
    speakers = cast_names([source]) if language == "Vietnamese" else []
    voices = speaker_voices(proposal, speakers) if speakers else {}
    addresses = speaker_addresses(proposal, speakers, voices, use_role_defaults=False) if len(speakers) == 2 else {}
    unanswered = context.context.unanswered_questions()
    instructions = PROMPT.read_text(encoding="utf-8")
    if voices or addresses:
        instructions += (
            "\nIf a character speaks, write from that named speaker's point of view and goal. "
            "speaker_self_references is their own pronoun; speaker_addresses is how they call the other person. "
            "Follow these saved choices over generic examples. Omit a pronoun when natural."
        )
    if unanswered:
        instructions += UNANSWERED_QUESTIONS_RULE
    request = StructuredRequest(
        stage="screenplay_generation", instructions=instructions + (
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
            **({"speaker_self_references": voices} if voices else {}),
            **({"speaker_addresses": addresses} if addresses else {}),
            **({"unanswered_questions": unanswered} if unanswered else {}),
            **({"revision_scope": "blocks", "block_ids": proposal.block_ids,
                "selected_blocks": [b.model_dump(mode="json") for b in target.blocks if b.id in proposal.block_ids]} if scoped else {}),
            "author_intent": context.context.ai_context(),
        }, ensure_ascii=False, separators=(",", ":")), response_model=BlockRevisionResult if scoped else SceneWritingResult)
    composed = provider.metadata.model == 'qwen2.5:7b' and can_compose(proposal, language)
    preserve_actions = (not composed and preserve_continuation_actions(proposal, source, position, language)
                        and can_compose(proposal, language, preserve_actions=True))
    composed = composed or preserve_actions
    if composed:
        request, beats = composition_request(proposal, language, preserve_actions=preserve_actions)
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
            output = (render_composition(request.response_model.model_validate(result.output.model_dump()), beats, language, json.loads(request.input_text))
                      if composed else SceneWritingResult.model_validate(result.output.model_dump()).scene)
            validate_writing_language(output.model_dump(), request.input_text)
        except (ValidationError, ValueError) as error:
            raise MalformedProviderResponseError("Invalid single-scene screenplay", raw_output=result.raw_output) from error
        scene = ScriptScene(id=target.id, source_scene_id=target.source_scene_id, heading=output.heading,
                            blocks=[{**b.model_dump(), "id": str(uuid4())} for b in output.blocks])
        parameters = proposal.parameters
        if composed:
            parameters = {**parameters, 'composition': 'source-preserving-v1',
                          'outline_reconciled': json.loads(request.input_text)['reconciled_ai_outline']}
            if json.loads(request.input_text)['dialogue_options']:
                parameters['dialogue_mode'] = 'bounded-reactions-v1'
        return proposal.model_copy(update={"scene": scene, "status": "ready", "model": result.model, "parameters": parameters})


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
