import json
from pathlib import Path
from uuid import uuid4

from pydantic import Field, ValidationError, create_model

from app.api.schemas.projects import SceneProposal
from app.api.schemas.scenes import Scene, SuggestedScene, SceneSuggestionResult, SingleSceneSuggestionResult
from app.application.ai_provider import MalformedProviderResponseError, StructuredProvider, StructuredRequest
from app.application.language import resolve_response_language
from app.application.progress import progress_step
from app.application.scene_count import SceneCountConflict, scene_count_bounds

PROMPT_VERSION = "scene-suggestions-v3"
PROMPT = Path(__file__).resolve().parents[3] / "domains/short-film/prompts/scene_suggestions_prompt.md"


def suggest_scenes(proposal: SceneProposal, provider: StructuredProvider, *, max_scenes: int = 60) -> SceneProposal:
    source = proposal.source_outline
    language = resolve_response_language(source.source.context.idea, source.source.response_language)
    response_model = SceneSuggestionResult if proposal.mode == "list" else SingleSceneSuggestionResult
    bounds = scene_count_bounds(source.source.context, max_scenes) if proposal.mode in {"list", "append"} else None
    if proposal.mode == "append" and len(source.scenes) >= bounds[1]:
        raise SceneCountConflict("Dàn cảnh đã đạt giới hạn số cảnh; hãy sửa giới hạn tác giả trước khi yêu cầu AI thêm cảnh.")
    if proposal.mode == "list" and bounds != (1, 60):
        response_model = create_model("BoundedSceneSuggestionResult", __base__=SceneSuggestionResult,
            scenes=(list[SuggestedScene], Field(min_length=bounds[0], max_length=bounds[1])))
    input_data = {
        "response_language": language, "mode": proposal.mode,
        "target_scene_id": proposal.target_scene_id, "author_request": proposal.instructions,
        "story_plan": source.source.draft.model_dump(mode="json"),
        "author_intent": source.source.context.model_dump(mode="json"),
        "scenes": [s.model_dump(mode="json") for s in source.scenes],
        **({"scene_count": {"minimum": bounds[0], "maximum": bounds[1]}} if proposal.mode == "list" else {}),
    }
    if proposal.mode == "append":
        input_data["reference_scenes"] = input_data.pop("scenes")
        after = (next(i for i, s in enumerate(source.scenes) if s.id == proposal.target_scene_id)
                 if proposal.target_scene_id is not None else len(source.scenes) - 1)
        input_data["insertion_context"] = {
            "after_scene_id": source.scenes[after].id if after >= 0 else None,
            "before_scene_id": source.scenes[after + 1].id if after + 1 < len(source.scenes) else None,
        }
    request = StructuredRequest(
        instructions=PROMPT.read_text(encoding="utf-8"), stage="scene_generation",
        input_text=json.dumps(input_data, ensure_ascii=False), response_model=response_model,
    )
    result = provider.request_structured(request)
    with progress_step("scene_validation"):
        try:
            output = response_model.model_validate(result.output.model_dump())
            if proposal.mode != "list" and len(output.scenes) != 1:
                raise ValueError("Single-scene request returned several scenes")
            if any(not s.title.strip() or not s.action.strip() for s in output.scenes):
                raise ValueError("Empty scene content")
        except (ValidationError, ValueError) as error:
            raise MalformedProviderResponseError("Invalid scene proposal", raw_output=result.raw_output) from error
        scenes, transitions = [], {}
        for item in output.scenes:
            data = item.model_dump(exclude={"transition"})
            if proposal.mode == "develop":
                original = next(s for s in source.scenes if s.id == proposal.target_scene_id)
                scene = original.model_copy(update=data)
            else:
                scene = Scene(id=str(uuid4()), **data)
            scenes.append(scene)
            transitions[scene.id] = item.transition
        return proposal.model_copy(update={"scenes": scenes, "transitions": transitions, "status": "ready", "model": result.model, "prompt_version": PROMPT_VERSION})
