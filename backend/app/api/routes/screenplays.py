from datetime import UTC, datetime
from uuid import uuid4

from pydantic import ValidationError

from fastapi import APIRouter, HTTPException

from app.api.routes import projects
from app.api.schemas.projects import ProjectResponse, RevisionRequest, Screenplay, ScreenplayProposal, ScreenplaySelection
from app.api.schemas.screenplays import ScriptScene, StartScreenplay, SceneWritingRequest, SelectScreenplay
from app.api.schemas.scenes import SceneId
from app.api.schemas.provenance import TextProvenance

from app.application.dataset import capture_workflow, recording_provider
from app.application.progress import progress_step
from app.application.screenplay_writing import PROMPT_VERSION, ScreenplayContextTooLarge, write_scene
from app.application.screenplay_composition import SceneSourceConflict
from app.application.screenplay_revisions import validate_request
from app.infrastructure.provider_factory import create_provider


def get_screenplay_provider():
    return create_provider()


router = APIRouter(prefix="/api/projects", tags=["screenplays"])


@router.post("/{project_id}/screenplay-selections", response_model=ProjectResponse)
def select_screenplay(project_id: str, request: SelectScreenplay):
    with projects.project_errors():
        project = projects.load_project(project_id)
        existing = next((s for s in project.screenplay_selections if s.id == request.request_id), None)
        if existing:
            if existing.source_version_id != request.source_version_id:
                raise HTTPException(409, "ID chọn bản đã dùng cho nguồn khác.")
            return project
        if project.revision != request.revision:
            raise projects.ProjectConflict
        script = project.screenplay if request.source_version_id == "current" else next(
            (v.screenplay for v in project.screenplay_versions if v.id == request.source_version_id), None)
        if script is None:
            raise HTTPException(404, "Không tìm thấy bản kịch bản đã lưu trong dự án.")
        incomplete = [str(i + 1) for i, s in enumerate(script.scenes)
            if not s.heading.strip() or not s.blocks or any(
                not b.text.strip() or (b.kind == "dialogue" and not b.speaker.strip()) for b in s.blocks)]
        if incomplete:
            raise HTTPException(422, "Cảnh chưa hoàn tất: " + ", ".join(incomplete)
                + ". Cần tên cảnh, nội dung khối và người nói cho lời thoại. Bạn vẫn lưu nháp được.")
        if len(project.screenplay_selections) >= 100:
            raise HTTPException(422, "Đã đủ 100 lần chọn nguồn; nguồn đã chọn vẫn giữ, bạn vẫn tự sửa và lưu được.")
        project.screenplay_selections.append(ScreenplaySelection(id=request.request_id,
            created_at=datetime.now(UTC).isoformat(), source_revision=project.revision,
            source_version_id=request.source_version_id, screenplay=script.model_copy(deep=True)))
        return projects.save_project(project)


@router.get("/{project_id}/screenplay-selections/{selection_id}/pdf")
def export_screenplay_pdf(project_id: str, selection_id: SceneId):
    from fastapi.responses import Response
    from reportlab.pdfbase.ttfonts import TTFError
    from app.application.screenplay_pdf import render_pdf, filename
    with projects.project_errors():
        project = projects.load_project(project_id)
        selection = next((s for s in project.screenplay_selections if s.id == selection_id), None)
        if selection is None:
            raise HTTPException(404, "Không tìm thấy bản kịch bản đã chọn trong dự án.")
        try:
            data = render_pdf(selection)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        except (OSError, TTFError) as error:
            raise HTTPException(503, "Chưa xuất được PDF. Bản đã chọn vẫn giữ; hãy kiểm tra font PDF và thử lại.") from error
        return Response(data, media_type="application/pdf", headers={
            "Content-Disposition": f'attachment; filename="{filename(selection)}"',
            "Cache-Control": "no-store",
            "Access-Control-Expose-Headers": "Content-Disposition",
        })


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
            raise HTTPException(422, "Cần lưu tên và diễn tiến của mọi cảnh trong dàn cảnh trước khi bắt đầu viết kịch bản.")
        projects.archive_screenplay(project)
        project.screenplay = Screenplay(
            id=request.request_id, version=1, source_revision=project.revision,
            source_outline=project.scene_outline.model_copy(deep=True),
            scenes=[ScriptScene(id=str(uuid4()), source_scene_id=s.id, heading=s.title)
                    for s in project.scene_outline.scenes])
        project.screenplay.provenance = {
            f"script:{scene.id}:heading": project.scene_outline.provenance.get(
                f"m2:{scene.source_scene_id}:title", TextProvenance())
            for scene in project.screenplay.scenes}
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
                if (existing.target_scene_id, existing.instructions, existing.scope, existing.block_ids, existing.review_id, existing.note_id) != (request.target_scene_id, request.instructions, request.scope, request.block_ids, request.review_id, request.note_id):
                    raise HTTPException(409, "ID tác vụ đã dùng cho cảnh hoặc yêu cầu khác.")
                return project
            if project.revision != request.revision:
                raise projects.ProjectConflict
            script = project.screenplay
            if script is None or not any(s.id == request.target_scene_id for s in script.scenes):
                raise HTTPException(422, "Chọn cảnh trong bản kịch bản đã lưu trước khi viết thử.")
            if any(p.status == "pending" for p in [*project.screenplay_proposals, *project.screenplay_reviews]):
                raise HTTPException(409, "Có lượt viết chưa rõ kết quả. Kiểm tra hoặc bỏ lượt đó trước; không tự chạy lại.")
            if len(project.screenplay_proposals) >= 100:
                raise HTTPException(422, "Đã đủ 100 lượt viết thử; vẫn tự viết và lưu kịch bản được.")
            instructions = validate_request(project, request)
            proposal = ScreenplayProposal(id=request.request_id, created_at=datetime.now(UTC).isoformat(),
                source_revision=project.revision, source_content=project.content_key(),
                source_screenplay=script.model_copy(deep=True),
                source_outline=project.scene_outline.model_copy(deep=True) if project.scene_outline else None,
                target_scene_id=request.target_scene_id, instructions=request.instructions, prompt_version=PROMPT_VERSION,
                scope=request.scope, block_ids=request.block_ids, review_id=request.review_id, note_id=request.note_id)
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
                    generated = write_scene(proposal.model_copy(update={"instructions": instructions}), provider)
                    proposal = generated.model_copy(update={"instructions": request.instructions})
                with progress_step("screenplay_proposal_save"):
                    project = ProjectResponse.model_validate(projects.get_project_store().update(project_id, keep_result))
                stored = next(p for p in project.screenplay_proposals if p.id == proposal.id)
                dataset.complete({"id": project.id, "proposal": stored.model_dump(mode="json")}, workflow_complete=False)
        except Exception as error:
            proposal.status, proposal.error = "failed", type(error).__name__
            projects.get_project_store().update(project_id, keep_result)
            if isinstance(error, (ScreenplayContextTooLarge, SceneSourceConflict)):
                raise HTTPException(422, str(error)) from error
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


class ApplyProposal(RevisionRequest):
    scene: ScriptScene | None = None


@router.post("/{project_id}/screenplay-revision-target")
def revision_target(project_id: str, request: SceneWritingRequest):
    from app.application.screenplay_revisions import resolve_target
    with projects.project_errors():
        p = projects.load_project(project_id, request.revision)
        return resolve_target(p, request.instructions, request.target_scene_id)


@router.post("/{project_id}/screenplay-proposals/{proposal_id}/apply", response_model=ProjectResponse)
def apply_proposal(project_id: str, proposal_id: SceneId, request: ApplyProposal):
    from app.api.schemas.projects import ProjectUpdate
    with projects.project_errors():
        p = projects.load_project(project_id)
        proposal = next((r for r in p.screenplay_proposals if r.id == proposal_id), None)
        if proposal is None:
            raise HTTPException(404, "Không tìm thấy phương án.")
        if proposal.status == "applied":
            if request.scene is not None and request.scene != proposal.applied_scene:
                raise projects.ProjectConflict
            return p
        if p.revision != request.revision:
            raise projects.ProjectConflict
        replacement = request.scene or proposal.preview_scene or proposal.scene
        if p.screenplay is None or replacement is None:
            raise projects.ProjectConflict
        script = p.screenplay.model_copy(deep=True)
        script.scenes = [replacement if s.id == proposal.target_scene_id else s for s in script.scenes]
        body = {key:getattr(p,key) for key in ("title","idea","constraints","answers","draft","response_language")}
        try:
            update = ProjectUpdate(**body, revision=p.revision,
                screenplay=script.model_dump(include={"id","version","scenes"}), screenplay_proposal_id=proposal_id,
                screenplay_proposal_previews={proposal_id:replacement})
        except ValidationError as error:
            raise HTTPException(422, "Phương án không khớp giới hạn hoặc ID của toàn bộ kịch bản; bản đang viết vẫn giữ nguyên.") from error
        return projects.update_project(project_id, update)


@router.post("/{project_id}/screenplay-proposals/{proposal_id}/undo", response_model=ProjectResponse)
def undo_proposal(project_id: str, proposal_id: SceneId, request: RevisionRequest):
    from app.application.provenance import scene_fields
    with projects.project_errors():
        p = projects.load_project(project_id)
        proposal = next((r for r in p.screenplay_proposals if r.id == proposal_id), None)
        if proposal is None or proposal.status != "applied" or proposal.applied_scene is None:
            raise HTTPException(409, "Không có lần nhận phương án để hoàn tác.")
        if proposal.undone_revision is not None:
            return p
        if p.revision != request.revision or p.screenplay is None or p.screenplay.id != proposal.source_screenplay.id or p.content_key() != proposal.source_content:
            raise projects.ProjectConflict
        current = next((s for s in p.screenplay.scenes if s.id == proposal.target_scene_id), None)
        if current != proposal.applied_scene or p.screenplay.source_outline != proposal.source_screenplay.source_outline:
            raise HTTPException(409, "Cảnh hoặc nguồn đã sửa sau khi nhận; không ghi đè để hoàn tác.")
        before = next(s for s in proposal.source_screenplay.scenes if s.id == proposal.target_scene_id)
        projects.archive_screenplay(p)
        affected = set(scene_fields([current,before], True))
        p.screenplay.provenance = {**{k:v for k,v in p.screenplay.provenance.items() if k not in affected},
            **{k:v for k,v in proposal.source_screenplay.provenance.items() if k in affected}}
        p.screenplay.scenes = [before.model_copy(deep=True) if s.id == before.id else s for s in p.screenplay.scenes]
        p.screenplay.version += 1
        try:
            p.screenplay = Screenplay.model_validate(p.screenplay.model_dump())
        except ValidationError as error:
            raise HTTPException(409, "Các ID khối đã được dùng ở nơi khác; không thể hoàn tác an toàn.") from error
        proposal.undone_revision = p.revision + 1
        return projects.save_project(p)
