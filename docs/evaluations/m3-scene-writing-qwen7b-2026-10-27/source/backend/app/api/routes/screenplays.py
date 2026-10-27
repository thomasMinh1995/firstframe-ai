from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.api.routes import projects
from app.api.schemas.projects import ProjectResponse, RevisionRequest, Screenplay, ScreenplayProposal
from app.api.schemas.screenplays import ScriptScene, StartScreenplay, SceneWritingRequest
from app.api.schemas.scenes import SceneId

from app.application.dataset import capture_workflow, recording_provider
from app.application.progress import progress_step
from app.application.screenplay_writing import PROMPT_VERSION, write_scene
from app.infrastructure.provider_factory import create_provider


def get_screenplay_provider():
    return create_provider()


router = APIRouter(prefix="/api/projects", tags=["screenplays"])


@router.post("/{project_id}/screenplay", response_model=ProjectResponse)
def start_screenplay(project_id: str, request: StartScreenplay):
    with projects.project_errors():
        project = projects.load_project(project_id)
        # A lost response must never create a second blank draft, even after later edits.
        known = [v.screenplay.id for v in project.screenplay_versions]
        if project.screenplay:
            known.append(project.screenplay.id)
        if request.request_id in known:
            return project
        if project.revision != request.revision:
            raise projects.ProjectConflict
        if not project.scene_handoff:
            raise HTTPException(422, "Cần lưu tên và diễn tiến của mọi cảnh M2 trước khi bắt đầu M3.")
        projects.archive_screenplay(project)
        project.screenplay = Screenplay(
            id=request.request_id, version=1, source_revision=project.revision,
            source_outline=project.scene_outline.model_copy(deep=True),
            scenes=[ScriptScene(id=str(uuid4()), source_scene_id=s.id, heading=s.title)
                    for s in project.scene_outline.scenes])
        return projects.save_project(project)


@router.post("/{project_id}/screenplay-versions/{version_id}/restore", response_model=ProjectResponse)
def restore_screenplay(project_id: str, version_id: SceneId, request: RevisionRequest):
    with projects.project_errors():
        project = projects.load_project(project_id, request.revision)
        version = next((v for v in project.screenplay_versions if v.id == version_id), None)
        if version is None or project.screenplay is None:
            raise HTTPException(404, "Không tìm thấy phiên bản kịch bản trong dự án.")
        next_version = max([project.screenplay.version, *[v.screenplay.version for v in project.screenplay_versions]]) + 1
        projects.archive_screenplay(project)
        project.screenplay = version.screenplay.model_copy(deep=True, update={"version": next_version})
        return projects.save_project(project)


@router.post("/{project_id}/screenplay-proposals/stream")
async def stream_scene_writing(project_id: str, request: SceneWritingRequest):
    return projects.project_stream(lambda: propose_scene(project_id, request))


@router.post("/{project_id}/screenplay-proposals", response_model=ProjectResponse)
def propose_scene(project_id: str, request: SceneWritingRequest):
    with projects.project_errors():
        with progress_step("screenplay_source"):
            project = projects.load_project(project_id)
            existing = next((p for p in project.screenplay_proposals if p.id == request.request_id), None)
            if existing:
                if (existing.target_scene_id, existing.instructions) != (request.target_scene_id, request.instructions):
                    raise HTTPException(409, "ID tác vụ đã dùng cho cảnh hoặc yêu cầu khác.")
                return project
            if project.revision != request.revision:
                raise projects.ProjectConflict
            script = project.screenplay
            if script is None or not any(s.id == request.target_scene_id for s in script.scenes):
                raise HTTPException(422, "Chọn cảnh trong bản kịch bản đã lưu trước khi viết thử.")
            if any(p.status == "pending" for p in project.screenplay_proposals):
                raise HTTPException(409, "Có lượt viết chưa rõ kết quả. Kiểm tra hoặc bỏ lượt đó trước; không tự chạy lại.")
            if len(project.screenplay_proposals) >= 100:
                raise HTTPException(422, "Đã đủ 100 lượt viết thử; vẫn tự viết và lưu kịch bản được.")
            proposal = ScreenplayProposal(id=request.request_id, created_at=datetime.now(UTC).isoformat(),
                source_revision=project.revision, source_content=project.content_key(),
                source_screenplay=script.model_copy(deep=True),
                source_outline=project.scene_outline.model_copy(deep=True) if project.scene_outline else None,
                target_scene_id=request.target_scene_id, instructions=request.instructions, prompt_version=PROMPT_VERSION)
            project.screenplay_proposals.append(proposal)
            projects.save_project(project, "screenplay_checkpoint")

        def keep_result(raw):
            for i, item in enumerate(raw.get("screenplay_proposals", [])):
                if item["id"] == proposal.id and item["status"] in {"pending", "discarded"}:
                    stored = proposal.model_copy(update={"status": "discarded"}) if item["status"] == "discarded" else proposal
                    raw["screenplay_proposals"][i] = stored.model_dump(mode="json")
                    break

        try:
            with capture_workflow("screenplay_writing", {"id": project.id, "proposal": proposal.model_dump(mode="json")}) as dataset:
                provider = recording_provider(get_screenplay_provider())
                metadata = provider.metadata
                proposal.provider, proposal.model, proposal.parameters = metadata.provider, metadata.model, metadata.parameters
                projects.get_project_store().update(project_id, keep_result)
                with progress_step("screenplay_generation"):
                    proposal = write_scene(proposal, provider)
                with progress_step("screenplay_proposal_save"):
                    project = ProjectResponse.model_validate(projects.get_project_store().update(project_id, keep_result))
                stored = next(p for p in project.screenplay_proposals if p.id == proposal.id)
                dataset.complete({"id": project.id, "proposal": stored.model_dump(mode="json")}, workflow_complete=False)
        except Exception as error:
            proposal.status, proposal.error = "failed", type(error).__name__
            projects.get_project_store().update(project_id, keep_result)
            raise
        return project


@router.post("/{project_id}/screenplay-proposals/{proposal_id}/discard", response_model=ProjectResponse)
def discard_scene_writing(project_id: str, proposal_id: SceneId, request: RevisionRequest):
    with projects.project_errors():
        project = projects.load_project(project_id, request.revision)
        proposal = next((p for p in project.screenplay_proposals if p.id == proposal_id), None)
        if proposal is None:
            raise HTTPException(404, "Không tìm thấy phương án trong dự án.")
        if proposal.status != "applied":
            proposal.status = "discarded"
        return projects.save_project(project)
