import json
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from app.api.schemas.projects import ScreenplayProposal
from app.api.schemas.screenplays import SceneWritingResult, ScriptScene
from app.application.ai_provider import MalformedProviderResponseError, ProviderRequestError, StructuredProvider, StructuredRequest, strict_json_instructions
from app.application.language import resolve_response_language
from app.application.progress import progress_step

PROMPT_VERSION = "screenplay-scene-v1"
PROMPT = Path(__file__).resolve().parents[3] / "domains/short-film/prompts/screenplay_scene_prompt.md"


class ScreenplayContextTooLarge(ProviderRequestError):
    pass


def write_scene(proposal: ScreenplayProposal, provider: StructuredProvider) -> ScreenplayProposal:
    script = proposal.source_screenplay
    target = next(s for s in script.scenes if s.id == proposal.target_scene_id)
    source = next(s for s in script.source_outline.scenes if s.id == target.source_scene_id)
    context = script.source_outline.source
    request = StructuredRequest(
        stage="screenplay_generation", instructions=PROMPT.read_text(encoding="utf-8"),
        input_text=json.dumps({
            "response_language": resolve_response_language(context.context.idea, context.response_language),
            "author_intent": context.context.ai_context(), "story_plan": context.draft.model_dump(mode="json"),
            "source_scenes": [s.model_dump(mode="json") for s in script.source_outline.scenes],
            "source_scene": source.model_dump(mode="json"), "target_scene_id": target.id,
            "screenplay_context": [s.model_dump(mode="json") for s in script.scenes],
            "author_request": proposal.instructions,
        }, ensure_ascii=False), response_model=SceneWritingResult)
    # Conservative UTF-8 byte budget; do not silently drop source to fit a local context.
    context_limit = provider.metadata.parameters.get("num_ctx", 16384)
    budget = min(12000, max(0, context_limit - 4096 - 512)) if isinstance(context_limit, int) else 12000
    if len(request.input_text.encode("utf-8")) + len(strict_json_instructions(request).encode("utf-8")) > budget:
        raise ScreenplayContextTooLarge("Ngữ cảnh vượt giới hạn viết thử hiện hỗ trợ; chưa gửi AI. Bản tác giả vẫn giữ, bạn có thể tiếp tục tự viết và lưu.")
    result = provider.request_structured(request)
    with progress_step("screenplay_validation"):
        try:
            output = SceneWritingResult.model_validate(result.output.model_dump()).scene
        except ValidationError as error:
            raise MalformedProviderResponseError("Invalid single-scene screenplay", raw_output=result.raw_output) from error
        scene = ScriptScene(id=target.id, source_scene_id=target.source_scene_id, heading=output.heading,
                            blocks=[{**b.model_dump(), "id": str(uuid4())} for b in output.blocks])
        return proposal.model_copy(update={"scene": scene, "status": "ready", "model": result.model})
