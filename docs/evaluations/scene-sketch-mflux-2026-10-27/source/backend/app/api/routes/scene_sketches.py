import time
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.api.routes import projects
from app.api.schemas.projects import ProjectResponse, RevisionRequest, SceneSketch
from app.api.schemas.scenes import SceneId, SketchRequest
from app.application.ai_provider import MissingProviderConfigurationError, ProviderError, ProviderTimeoutError
from app.application.progress import progress_step
from app.infrastructure.scene_images import MfluxSceneProvider, SceneImageStore, sketch_prompt

router = APIRouter(prefix="/api/projects", tags=["scene-sketches"])


def get_image_provider():
    return MfluxSceneProvider()


def get_image_store():
    return SceneImageStore(projects.get_project_store().path.parent / "scene-images")


@router.post("/{project_id}/scene-sketches/stream")
async def stream_sketch(project_id: str, request: SketchRequest):
    return projects.project_stream(lambda: create_sketch(project_id, request))


@router.post("/{project_id}/scene-sketches", response_model=ProjectResponse)
def create_sketch(project_id: str, request: SketchRequest):
    with projects.project_errors():
        project = projects.load_project(project_id)
        existing = next((s for s in project.scene_sketches if s.id == request.request_id), None)
        if existing:
            if (existing.scene_id, existing.instructions) != (request.scene_id, request.instructions):
                raise HTTPException(409, "ID yêu cầu đã dùng cho cảnh hoặc yêu cầu khác.")
            return project
        if project.revision != request.revision:
            raise projects.ProjectConflict
        outline = project.scene_outline
        scene = next((s for s in outline.scenes if s.id == request.scene_id), None) if outline else None
        if scene is None or not scene.action.strip():
            raise HTTPException(422, "Cần chọn cảnh và lưu diễn tiến trước khi phác hình.")
        if len(project.scene_sketches) >= 20:
            raise HTTPException(422, "Đã có 20 lượt phác trong dự án; vẫn có thể lưu và viết tiếp không cần ảnh.")
        if any(s.status == "pending" for s in project.scene_sketches):
            raise HTTPException(409, "Có yêu cầu ảnh chưa rõ kết quả. Kiểm tra hoặc bỏ yêu cầu đó trước; không tự chạy lại.")
        provider = get_image_provider()
        sketch = SceneSketch(id=request.request_id, scene_id=scene.id, created_at=datetime.now(UTC).isoformat(),
            source_revision=project.revision, source_content=project.content_key(),
            source_outline=outline.model_copy(deep=True), instructions=request.instructions,
            prompt=sketch_prompt(scene, outline.source.context, request.instructions),
            model=provider.model, parameters=dict(provider.parameters))
        project.scene_sketches.append(sketch)
        projects.save_project(project, "sketch_checkpoint")

        def keep_result(raw):
            for index, item in enumerate(raw.get("scene_sketches", [])):
                if item["id"] == sketch.id:
                    stored = sketch.model_copy(update={"status": "discarded"}) if item["status"] == "discarded" else sketch
                    raw["scene_sketches"][index] = stored.model_dump(mode="json")
                    break

        started = time.monotonic()
        failure = None
        try:
            with progress_step("sketch_generation"):
                image = provider.generate(sketch.prompt)
            with progress_step("sketch_validation"):
                asset_id = str(uuid4())
                get_image_store().save(project.id, asset_id, image)
                sketch.asset_id, sketch.status = asset_id, "ready"
        except Exception as error:
            sketch.status, sketch.error = "failed", type(error).__name__
            sketch.diagnostic = str(error)[:20000]
            failure = error
        sketch.duration_seconds = round(time.monotonic() - started, 3)
        result = ProjectResponse.model_validate(projects.get_project_store().update(project_id, keep_result))
        if failure:
            if isinstance(failure, MissingProviderConfigurationError):
                raise HTTPException(503, "Chưa sẵn sàng MFLUX local/model cache. Bản đang viết vẫn giữ; kiểm tra lượt ảnh đã lưu.") from failure
            if isinstance(failure, ProviderTimeoutError):
                raise HTTPException(504, "Phác hình vượt 180 giây. Kiểm tra lượt ảnh đã lưu; không tự retry.") from failure
            if isinstance(failure, (ProviderError, OSError)):
                raise HTTPException(502, "Chưa tạo/lưu được ảnh hợp lệ. Text và ảnh đã giữ vẫn nguyên; kiểm tra lượt ảnh đã lưu.") from failure
            raise failure
        return result


def find_sketch(project, sketch_id):
    sketch = next((s for s in project.scene_sketches if s.id == sketch_id), None)
    if sketch is None:
        raise HTTPException(404, "Không tìm thấy ảnh trong dự án này.")
    return sketch


@router.post("/{project_id}/scene-sketches/{sketch_id}/keep", response_model=ProjectResponse)
def keep_sketch(project_id: str, sketch_id: SceneId, request: RevisionRequest):
    with projects.project_errors():
        project = projects.load_project(project_id, request.revision)
        sketch = find_sketch(project, sketch_id)
        if sketch.id not in project.applicable_sketch_ids or not sketch.asset_id:
            raise HTTPException(409, "Ảnh chưa sẵn sàng, đã bỏ hoặc nguồn đã đổi; không chọn kết quả cũ.")
        try:
            get_image_store().read(project.id, sketch.asset_id)
        except (OSError, ProviderError) as error:
            raise HTTPException(409, "Tệp ảnh thiếu hoặc lỗi; text và ảnh đã giữ vẫn nguyên.") from error
        project.selected_scene_sketches[sketch.scene_id] = sketch.id
        return projects.save_project(project)


@router.post("/{project_id}/scene-sketches/{sketch_id}/discard", response_model=ProjectResponse)
def discard_sketch(project_id: str, sketch_id: SceneId, request: RevisionRequest):
    with projects.project_errors():
        project = projects.load_project(project_id, request.revision)
        sketch = find_sketch(project, sketch_id)
        sketch.status = "discarded"
        if project.selected_scene_sketches.get(sketch.scene_id) == sketch.id:
            del project.selected_scene_sketches[sketch.scene_id]
        return projects.save_project(project)


@router.get("/{project_id}/scene-sketches/{sketch_id}/image")
def read_sketch(project_id: str, sketch_id: SceneId):
    with projects.project_errors():
        project = projects.load_project(project_id)
        sketch = find_sketch(project, sketch_id)
        if not sketch.asset_id:
            raise HTTPException(404, "Chưa có tệp ảnh.")
        try:
            data = get_image_store().read(project.id, sketch.asset_id)
        except (OSError, ProviderError) as error:
            raise HTTPException(404, "Tệp ảnh thiếu hoặc lỗi; vẫn có thể lưu và viết tiếp.") from error
        return Response(content=data, media_type="image/png", headers={"Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff", "Content-Security-Policy": "default-src 'none'; sandbox"})
