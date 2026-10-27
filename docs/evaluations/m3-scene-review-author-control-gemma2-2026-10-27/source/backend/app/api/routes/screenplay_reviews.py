from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from app.api.routes import projects
from app.api.schemas.projects import ProjectResponse, RevisionRequest, ScreenplayReview
from app.api.schemas.screenplays import ReviewAssessment, SceneWritingRequest
from app.api.schemas.scenes import SceneId
from app.application.dataset import capture_workflow, recording_provider
from app.application.progress import progress_step
from app.application.screenplay_context import ScreenplayContextTooLarge
from app.application.screenplay_review import PROMPT_VERSION, review_scene, review_sources
from app.infrastructure.provider_factory import create_provider

router = APIRouter(prefix="/api/projects", tags=["screenplay-reviews"])


def get_review_provider():
    return create_provider()


@router.post("/{project_id}/screenplay-reviews/stream")
async def stream_review(project_id: str, request: SceneWritingRequest):
    return projects.project_stream(lambda: create_review(project_id, request))


@router.post("/{project_id}/screenplay-reviews", response_model=ProjectResponse)
def create_review(project_id: str, request: SceneWritingRequest):
    with projects.project_errors():
        with progress_step("screenplay_review_source"):
            project = projects.load_project(project_id)
            existing = next((r for r in project.screenplay_reviews if r.id == request.request_id), None)
            if existing:
                if (existing.target_scene_id, existing.instructions) != (request.target_scene_id, request.instructions):
                    raise HTTPException(409, "ID góp ý đã dùng cho yêu cầu khác.")
                return project
            if project.revision != request.revision:
                raise projects.ProjectConflict
            script = project.screenplay
            target = next((s for s in script.scenes if s.id == request.target_scene_id), None) if script else None
            if target is None or not any(b.text.strip() for b in target.blocks):
                raise HTTPException(422, "Cần chọn cảnh và lưu ít nhất một khối có nội dung để nhận góp ý. Bạn vẫn lưu nháp được.")
            if any(r.status == "pending" for r in [*project.screenplay_reviews, *project.screenplay_proposals]):
                raise HTTPException(409, "Có lượt AI chưa rõ kết quả; kiểm tra hoặc bỏ trước khi chủ động gọi lượt mới.")
            if len(project.screenplay_reviews) >= 100:
                raise HTTPException(422, "Đã đủ 100 lượt góp ý; bạn vẫn tự sửa và lưu được.")
            review = ScreenplayReview(id=request.request_id, created_at=datetime.now(UTC).isoformat(),
                source_revision=project.revision, source_content=project.content_key(),
                source_screenplay=script.model_copy(deep=True),
                source_outline=project.scene_outline.model_copy(deep=True) if project.scene_outline else None,
                target_scene_id=target.id, instructions=request.instructions, prompt_version=PROMPT_VERSION)
            review.sources = review_sources(review)
            project.screenplay_reviews.append(review)
            projects.save_project(project, "screenplay_review_checkpoint")

        def keep_result(raw):
            for i, item in enumerate(raw.get("screenplay_reviews", [])):
                if item["id"] == review.id and item["status"] in {"pending", "discarded"}:
                    stored = review.model_copy(update={"status": "discarded"}) if item["status"] == "discarded" else review
                    raw["screenplay_reviews"][i] = stored.model_dump(mode="json")
                    break
        try:
            with capture_workflow("screenplay_review", {"id": project.id, "review": review.model_dump(mode="json")}) as dataset:
                provider = recording_provider(get_review_provider())
                metadata = provider.metadata
                review.provider, review.model, review.parameters = metadata.provider, metadata.model, metadata.parameters
                projects.get_project_store().update(project_id, keep_result)
                review = review_scene(review, provider)
                with progress_step("screenplay_review_save"):
                    project = ProjectResponse.model_validate(projects.get_project_store().update(project_id, keep_result))
                stored = next(r for r in project.screenplay_reviews if r.id == review.id)
                dataset.complete({"id": project.id, "review": stored.model_dump(mode="json")}, workflow_complete=False)
        except Exception as error:
            review.status, review.error = "failed", type(error).__name__
            projects.get_project_store().update(project_id, keep_result)
            if isinstance(error, ScreenplayContextTooLarge):
                raise HTTPException(422, str(error)) from error
            raise
        return project


def find_review(project, review_id):
    review = next((r for r in project.screenplay_reviews if r.id == review_id), None)
    if review is None:
        raise HTTPException(404, "Không tìm thấy góp ý trong dự án.")
    return review


@router.post("/{project_id}/screenplay-reviews/{review_id}/discard", response_model=ProjectResponse)
def discard_review(project_id: str, review_id: SceneId, request: RevisionRequest):
    with projects.project_errors():
        project = projects.load_project(project_id, request.revision)
        find_review(project, review_id).status = "discarded"
        return projects.save_project(project)


@router.post("/{project_id}/screenplay-reviews/{review_id}/notes/{note_id}/assessment", response_model=ProjectResponse)
def assess_note(project_id: str, review_id: SceneId, note_id: SceneId, request: ReviewAssessment):
    with projects.project_errors():
        project = projects.load_project(project_id, request.revision)
        review = find_review(project, review_id)
        note = next((n for n in review.notes if n.id == note_id), None)
        if review.status != "ready" or note is None:
            raise HTTPException(404, "Không tìm thấy nhận xét đã lưu.")
        note.assessment = request.assessment
        return projects.save_project(project)
