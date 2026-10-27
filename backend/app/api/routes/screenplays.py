from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.api.routes import projects
from app.api.schemas.projects import ProjectResponse, RevisionRequest, Screenplay
from app.api.schemas.screenplays import ScriptScene, StartScreenplay
from app.api.schemas.scenes import SceneId

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
