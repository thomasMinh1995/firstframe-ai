from hashlib import sha256
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.api.routes import projects, screenplays, screenplay_reviews
from app.api.schemas.projects import ProjectResponse, StoryDraft
from app.api.schemas.screenplays import ScreenplayEdit
from app.api.schemas.scenes import SceneId
from app.api.schemas.draft_runs import DraftRunResponse
from app.application import draft_workflow as workflow
from app.application import draft_progress as progress
from app.application.draft_run_store import DraftRunStore, active_run
from app.application.language import resolve_response_language
from app.application.provenance import attribute_edits, draft_fields, scene_fields
from app.application.project_store import ProjectConflict
from app.application.workflow import create_provider

router = APIRouter(prefix="/api/projects/{project_id}/draft-runs", tags=["draft-runs"])


def store():
    return DraftRunStore(projects.get_project_store().path)


def providers():
    return [create_provider(), projects.get_scene_provider(), screenplays.get_screenplay_provider(), screenplay_reviews.get_review_provider()]


def brief(run):
    result = {k: v for k, v in run.items() if k not in (
        "candidate", "original", "source_content", "calls", "config", "owner", "plan_review_result",
    )}
    result.update(progress.public_progress(run))
    config = None
    if run["status"] in ("needs_input", "partial", "failed", "interrupted"):
        try:
            config = workflow.configuration(providers())
        except Exception:
            pass  # Reading saved work must remain available when AI is unconfigured.
    reason = progress.continuation_block(run, config)
    result.update(can_continue=reason is None, continue_block_reason=reason,
                  continue_block_message=progress.CONTINUE_MESSAGES.get(reason))
    # Provider errors can contain prompts or raw model output. Keep them private.
    if result["error"]:
        result["error"] = "Lượt tạo gặp lỗi. Phần đã lưu vẫn được giữ; hãy kiểm tra trạng thái trước khi tiếp tục."
    if result["review_error"]:
        result["review_error"] = "Góp ý chưa hoàn tất. Bản nháp đã lưu vẫn đọc được."
    return DraftRunResponse.model_validate(result).model_dump(mode="json")


class Start(BaseModel):
    revision_instructions: str = Field(default="", max_length=2000)
    model_config = ConfigDict(extra="forbid")
    request_id: SceneId
    revision: int = Field(ge=0)


class Continue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_revision: int = Field(ge=0)
    answers: list[str] | None = Field(default=None, max_length=20)


class CandidateEdit(BaseModel):
    save_id: SceneId | None = None
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=0)
    draft: StoryDraft | None = None
    answers: list[str] | None = Field(default=None, max_length=20)
    screenplay: ScreenplayEdit | None = None


class Adopt(Continue):
    revision: int = Field(ge=0)


@asynccontextmanager
async def lifespan(app):
    store().recover(workflow.OWNER)
    yield


@router.get("", response_model=list[DraftRunResponse])
def list_runs(project_id: str):
    with projects.project_errors():
        projects.load_project(project_id)
        return [brief(r) for r in store().rows(project_id)]


@router.post("", response_model=DraftRunResponse)
def start(project_id: str, request: Start):
    with projects.project_errors():
        s = store()
        old = next((r for r in s.rows(project_id) if r["id"] == request.request_id), None)
        if old:
            if old["source_revision"] != request.revision or old.get("revision_instructions", "") != request.revision_instructions:
                raise ProjectConflict
            return brief(old)
        if any(active_run(r) for r in s.rows(project_id)):
            raise HTTPException(409, "Đang có một lượt tạo chưa kết thúc. Hãy mở lại tiến độ hoặc kết thúc lượt đó trước khi tạo mới.")
        p = projects.load_project(project_id, request.revision)
        if not p.idea.strip():
            raise HTTPException(422, "Hãy nhập ý tưởng trước khi tạo bản nháp.")
        if request.revision_instructions and len(p.constraints) >= 20:
            raise HTTPException(422, "Hãy gộp bớt giới hạn trước khi thêm yêu cầu cấu trúc mới.")
        resolve_response_language(p.idea, p.response_language)
        selected = providers()
        run, created = s.create_run(project_id, request.request_id, request.revision,
            workflow.configuration(selected), workflow.OWNER, request.revision_instructions)
        if created:
            workflow.launch(s, project_id, run["id"], selected)
        return brief(run)


@router.get("/{run_id}", response_model=DraftRunResponse)
def status(project_id: str, run_id: SceneId):
    with projects.project_errors():
        return brief(store().get_run(project_id, run_id))


def candidate_response(run):
    return {"revision": run["candidate_revision"], "save_id": run.get("last_candidate_save_id"),
            "project": ProjectResponse.model_validate(run["candidate"]),
            "plan_review": run.get("plan_review_result")}


@router.get("/{run_id}/candidate")
def candidate(project_id: str, run_id: SceneId):
    with projects.project_errors():
        return candidate_response(store().get_run(project_id, run_id))


@router.put("/{run_id}/candidate")
def edit_candidate(project_id: str, run_id: SceneId, request: CandidateEdit):
    with projects.project_errors():
        fingerprint = sha256(request.model_dump_json().encode()).hexdigest()
        def edit(r):
            if request.save_id and r.get("last_candidate_save_id") == request.save_id:
                if r.get("candidate_fingerprint") != fingerprint or r["candidate_revision"] != request.revision + 1:
                    raise ProjectConflict
                return
            if r["status"] not in ("needs_input", "ready", "partial", "failed", "interrupted", "cancelled") or r["candidate_revision"] != request.revision or r["adopted_revision"] is not None:
                raise ProjectConflict
            previous = r["candidate"]
            p = ProjectResponse.model_validate(previous)
            if p.draft is None and r["status"] != "needs_input":
                raise ProjectConflict
            if request.answers is not None:
                if len(request.answers) != len(p.answers) or any(len(a) > 2000 for a in request.answers):
                    raise ProjectConflict
                if r["status"] != "needs_input" and request.answers != p.answers:
                    raise ProjectConflict
                p.answers = request.answers
            if p.draft is not None and request.draft is None:
                raise HTTPException(422, "Giữ story plan của candidate khi sửa.")
            if p.draft is not None:
                r["original"] = r["original"] or r["candidate"]
            p.draft_provenance = attribute_edits(p.draft_provenance, draft_fields(p.draft), draft_fields(request.draft))
            p.draft = request.draft
            if request.screenplay is not None:
                edit, script = request.screenplay, p.screenplay
                if script is None or (edit.id, edit.version) != (script.id, script.version) or [(s.id, s.source_scene_id) for s in edit.scenes] != [(s.id, s.source_scene_id) for s in script.scenes]:
                    raise ProjectConflict
                owners = {b.id: s.id for s in script.scenes for b in s.blocks}
                if any(b.id in owners and owners[b.id] != s.id for s in edit.scenes for b in s.blocks):
                    raise ProjectConflict
                script.provenance = attribute_edits(script.provenance, scene_fields(script.scenes, True), scene_fields(edit.scenes, True))
                script.scenes = edit.scenes
                script.version += 1
                r["completed_scenes"] = sum(bool(s.heading.strip() and s.blocks and all(
                    b.text.strip() and (b.kind != "dialogue" or b.speaker.strip()) for b in s.blocks)) for s in script.scenes)
                if r["status"] == "ready" and r["completed_scenes"] != r["total_scenes"]:
                    r["status"] = "partial"
            r["candidate"] = p.model_dump(mode="json")
            r["candidate_revision"] += 1
            r.update(last_candidate_save_id=request.save_id, candidate_fingerprint=fingerprint)
            progress.candidate_edited(r, previous)
        r = store().change(project_id, run_id, edit)
        return candidate_response(r)


@router.post("/{run_id}/continue", response_model=DraftRunResponse)
def resume(project_id: str, run_id: SceneId, request: Continue):
    with projects.project_errors():
        selected = providers()
        def claim(r):
            if r["candidate_revision"] != request.candidate_revision or r["status"] not in ("needs_input", "partial", "failed", "interrupted") or r["adopted_revision"] is not None:
                raise ProjectConflict
            reason = progress.continuation_block(r, workflow.configuration(selected))
            if reason:
                raise HTTPException(409, progress.CONTINUE_MESSAGES[reason])
            p = ProjectResponse.model_validate(r["candidate"])
            if request.answers is not None:
                if r["status"] != "needs_input" or p.analysis is None or len(request.answers) != len(p.analysis.missing_information) or any(len(a) > 2000 for a in request.answers):
                    raise HTTPException(422, "Câu trả lời không khớp câu hỏi của lượt này.")
                p.answers = request.answers
                r["candidate"] = p.model_dump(mode="json")
            r.update(status="running", owner=workflow.OWNER, sending=False, error=None)
            r["candidate_revision"] += 1
        s = store()
        run = s.change(project_id, run_id, claim)
        workflow.launch(s, project_id, run_id, selected)
        return brief(run)


@router.post("/{run_id}/cancel", response_model=DraftRunResponse)
def cancel(project_id: str, run_id: SceneId):
    with projects.project_errors():
        def stop(r):
            if r["adopted_revision"] is not None:
                raise ProjectConflict
            r["cancel_requested"] = True
            if r["status"] != "running":
                r["status"] = "cancelled"
                progress.end_items(r, "cancelled", "cancelled")
        return brief(store().change(project_id, run_id, stop))


@router.post("/{run_id}/adopt", response_model=ProjectResponse)
def adopt(project_id: str, run_id: SceneId, request: Adopt):
    with projects.project_errors():
        return store().adopt(project_id, run_id, request.revision, request.candidate_revision)
