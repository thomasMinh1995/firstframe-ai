import asyncio
import json
import logging
from hashlib import sha256
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.api.routes.generate import _to_response, get_story_generation_service
from app.api.schemas.projects import (
    AuthorContext,
    ClarificationVersion,
    DraftVersion,
    FeedbackSource,
    PlanGeneration,
    ProjectResponse,
    ProjectSummary,
    ProjectUpdate,
    RevisionRequest,
    StoryDraft,
    ScreenplayVersion,
    SceneOutline,
    SceneOutlineVersion,
    ScenePlanSource,
    SceneProposal,
    author_context,
)
from app.api.schemas.scenes import StartSceneOutline, SceneSuggestionRequest
from app.application.scene_staging import PROMPT_VERSION as STAGING_PROMPT_VERSION, suggest_staging
from app.api.schemas.story import AnalysisNoteResponse, AnalysisResponse, EvaluationResponse
from app.application.ai_provider import (
    MalformedProviderResponseError,
    MissingProviderConfigurationError,
    ProviderRequestError,
    ProviderTimeoutError,
    ProviderError,
)
from app.application.dataset import capture_workflow, recording_provider
from app.application.scene_suggestions import PROMPT_VERSION, suggest_scenes
from app.application.provenance import attribute_edits, scene_fields, draft_fields, ai_draft
from app.infrastructure.provider_factory import create_provider
from app.application.clarification import MAX_CHOICES, conversation_questions
from app.application.language import LanguageSelectionRequired, resolve_response_language
from app.application.progress import progress_listener, report_progress, progress_step
from app.application.project_store import ProjectConflict, ProjectNotFound, ProjectStore
from app.application.revision_review import review_context
from app.core.artifacts import Constraint, PlanSection, StoryPlanArtifact

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("/{project_id}/scene-suggestions/stream")
async def stream_scene_suggestions(project_id: str, request: SceneSuggestionRequest):
    return project_stream(lambda: scene_suggestions(project_id, request))


@router.post("/{project_id}/{operation}/stream")
async def stream_project_operation(
    project_id: str, operation: Literal["analyze", "clarify", "plan", "review"], request: RevisionRequest
):
    handler = {"analyze": analyze_project, "clarify": clarify_project, "plan": plan_project, "review": review_project}
    return project_stream(lambda: handler[operation](project_id, request))


def project_stream(action):
    events: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def work():
        def publish(event):
            loop.call_soon_threadsafe(events.put_nowait, event)

        token = progress_listener.set(publish)
        try:
            result = action()
            publish({"type": "result", "project": result.model_dump(mode="json")})
        except HTTPException as error:
            publish({"type": "error", "detail": error.detail})
        except Exception:
            logging.getLogger(__name__).exception("Streamed project operation failed")
            publish({"type": "error", "detail": "Không hoàn tất được thao tác. Hãy mở lại dự án để kiểm tra nội dung đã lưu."})
        finally:
            progress_listener.reset(token)

    async def stream():
        task = asyncio.create_task(asyncio.to_thread(work))
        try:
            while True:
                try:
                    event = await asyncio.wait_for(events.get(), timeout=15)
                except TimeoutError:
                    yield "\n"
                    continue
                yield json.dumps(event, ensure_ascii=False) + "\n"
                if event["type"] in {"result", "error"}:
                    break
        finally:
            # The existing operation finishes saving even if the browser disconnects.
            await asyncio.shield(task)

    return StreamingResponse(stream(), media_type="application/x-ndjson", headers={
        "Cache-Control": "no-cache", "X-Accel-Buffering": "no",
    })


def get_project_store() -> ProjectStore:
    return ProjectStore(Path(__file__).resolve().parents[3] / ".data" / "projects.sqlite3")


@contextmanager
def project_errors():
    try:
        yield
    except ProjectNotFound as error:
        raise HTTPException(404, "Project not found.") from error
    except LanguageSelectionRequired as error:
        raise HTTPException(422, str(error)) from error
    except ProjectConflict as error:
        raise HTTPException(
            409, "Dự án đã thay đổi ở cửa sổ khác. Hãy tải bản sao trước khi mở lại dự án."
        ) from error
    except MissingProviderConfigurationError as error:
        raise HTTPException(
            503, "Chưa cấu hình AI hoặc chưa cài model Ollama. Hãy kiểm tra cấu hình backend."
        ) from error
    except ProviderTimeoutError as error:
        raise HTTPException(
            504, "AI phản hồi quá lâu. Nội dung đã lưu vẫn được giữ; hãy thử lại."
        ) from error
    except (ProviderRequestError, MalformedProviderResponseError) as error:
        raise HTTPException(502, "Chưa nhận được phản hồi hợp lệ từ AI. Hãy thử lại.") from error


def load_project(project_id: str, revision: int | None = None) -> ProjectResponse:
    project = ProjectResponse.model_validate(get_project_store().get(project_id))
    if revision is not None and project.revision != revision:
        raise ProjectConflict
    return project


def save_project(project: ProjectResponse, stage: str = "saving") -> ProjectResponse:
    with progress_step(stage):
        if stage != "autosaving":
            project.edit_sessions = {}
        data = project.model_dump(exclude_computed_fields=True)
        return ProjectResponse.model_validate(get_project_store().save(data, project.revision))


def dataset_snapshot(project: ProjectResponse) -> dict[str, object]:
    return project.model_dump(mode="json", exclude={
        "last_save_id", "last_save_revision", "last_save_fingerprint", "edit_sessions",
        "versions", "clarification_history", "plan_generations", "applicable_plan_ids",
        "scene_proposals", "staging_proposals", "applicable_scene_proposal_ids",
        "scene_sketches", "selected_scene_sketches", "applicable_sketch_ids",
        "screenplay", "screenplay_versions", "screenplay_source_is_current",
        "screenplay_proposals", "applicable_screenplay_proposal_ids",
        "screenplay_reviews", "current_screenplay_review_ids",
        "screenplay_selections", "screenplay_handoff",
    })


def constraints_for(project: ProjectResponse) -> tuple[Constraint, ...]:
    return tuple(
        Constraint(name=f"constraint-{i}", value=value)
        for i, value in enumerate(project.constraints)
    )


def attach_feedback_source(project: ProjectResponse, context: AuthorContext) -> None:
    assert project.feedback is not None and project.draft is not None
    project.reviewed_content = project.content_key()
    project.feedback_source = FeedbackSource(
        project_id=project.id, artifact_id=project.feedback.artifact_id,
        revision=project.revision, content_key=project.reviewed_content,
        context=context.model_copy(deep=True), draft=project.draft.model_copy(deep=True),
    )


def add_version(project: ProjectResponse) -> None:
    if project.draft is not None:
        version = DraftVersion(
            response_language=project.response_language,
            id=str(uuid4()),
            created_at=datetime.now(UTC).isoformat(),
            idea=project.idea,
            constraints=project.constraints,
            questions=project.analysis.missing_information if project.analysis else [],
            answers=project.answers,
            clarifications=dict(project.creator_answers()),
            draft=project.draft.model_copy(deep=True),
            draft_provenance=project.draft_provenance.copy(),
            feedback=project.feedback if project.feedback_is_current else None,
            feedback_source=project.feedback_source.model_copy(deep=True)
            if project.feedback_is_current and project.feedback_source else None,
        )
        if project.versions and project.versions[-1].model_dump(
            exclude={"id", "created_at"}
        ) == version.model_dump(exclude={"id", "created_at"}):
            return
        project.versions.append(version)


def archive_clarifications(project: ProjectResponse, answers: list[str] | None = None) -> None:
    answers = project.answers if answers is None else answers
    clarifications = dict(project.creator_answers(answers))
    if not clarifications:
        return
    version = ClarificationVersion(
        response_language=project.response_language,
        id=str(uuid4()),
        created_at=datetime.now(UTC).isoformat(),
        idea=project.idea,
        constraints=project.constraints,
        questions=project.analysis.missing_information if project.analysis else [],
        answers=answers,
        clarifications=clarifications,
    )
    if project.clarification_history and project.clarification_history[-1].model_dump(
        exclude={"id", "created_at"}
    ) == version.model_dump(exclude={"id", "created_at"}):
        return
    project.clarification_history.append(version)


@router.get("", response_model=list[ProjectSummary])
def list_projects():
    return get_project_store().list()


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project():
    project = ProjectResponse(id=str(uuid4()), updated_at=datetime.now(UTC).isoformat())
    return get_project_store().create(project.model_dump(exclude_computed_fields=True))


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str):
    with project_errors():
        return load_project(project_id)


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, request: ProjectUpdate):
    with project_errors():
        project = load_project(project_id)
        fingerprint = sha256(json.dumps(request.model_dump(exclude={"revision"}, exclude_unset=True),
            sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        if request.save_id and request.save_id == project.last_save_id:
            if fingerprint != project.last_save_fingerprint:
                raise HTTPException(409, "Mã lưu đã dùng cho nội dung khác.")
            return project
        if project.revision != request.revision:
            raise ProjectConflict
        if request.save_mode == "autosave" and request.edit_session_id is None:
            raise HTTPException(422, "Lưu tự động cần mã phiên chỉnh sửa.")
        boundary = bool(request.scene_proposal_id or request.staging_use
                        or request.screenplay_proposal_id or request.restore_draft_id)
        def checkpoint(artifact):
            needed = (boundary or request.save_mode != "autosave"
                      or project.edit_sessions.get(artifact) != request.edit_session_id)
            if request.edit_session_id:
                project.edit_sessions[artifact] = request.edit_session_id
            return needed
        ai_scene_fields, ai_script_fields, confirmed = None, None, set()
        questions = project.analysis.missing_information if project.analysis else []
        if len(request.answers) != len(questions):
            raise HTTPException(422, "Câu trả lời phải khớp với bộ câu hỏi hiện tại.")
        if request.staging_use is not None:
            use = request.staging_use
            proposal = next((p for p in project.staging_proposals if p.id == use.proposal_id), None)
            idea = next((i for i in proposal.staging_ideas if i.id == use.idea_id), None) if proposal else None
            if (proposal is None or proposal.mode != "staging" or idea is None or idea.status != "available"
                    or use.proposal_id not in project.applicable_scene_proposal_ids):
                raise HTTPException(409, "Ý góp ý đã dùng/bỏ hoặc nguồn đã đổi. Bản đang sửa vẫn được giữ.")
            if request.scene_proposal_id is not None or request.scene_outline is None or not use.value.strip():
                raise HTTPException(422, "Chỉ dùng một ý góp ý có nội dung mỗi lần lưu.")
            expected = project.scene_outline.model_copy(deep=True)
            target = next(s for s in expected.scenes if s.id == proposal.target_scene_id)
            target.staging_choices[idea.field] = use.value
            if (request.scene_outline.id != expected.id or request.scene_outline.version != expected.version
                    or request.scene_outline.scenes != expected.scenes
                    or any(getattr(request, key) != getattr(project, key)
                           for key in ("idea", "constraints", "answers", "draft", "response_language"))):
                raise HTTPException(409, "Dùng ý chỉ thay đúng mục đã nêu. Giữ thành bản tự chỉnh nếu muốn sửa các phần khác.")
            idea.status = "applied"
            idea.applied_text = use.value
            idea.applied_revision = project.revision + 1
            key = f"m2:{proposal.target_scene_id}:staging:{idea.field}"
            ai_scene_fields = {key: idea.suggestion}
            confirmed.add(key)
        for idea_id, text in request.staging_idea_edits.items():
            owner = next((p for p in project.staging_proposals if any(i.id == idea_id for i in p.staging_ideas)), None)
            idea = next((i for i in owner.staging_ideas if i.id == idea_id), None) if owner else None
            if (owner is None or owner.status != "ready" or idea is None
                    or (idea.status != "available" and not (request.staging_use and request.staging_use.idea_id == idea_id))):
                raise HTTPException(409, "Ý góp ý đã đổi trạng thái; phần tự chỉnh vẫn được giữ.")
            idea.preview_text = text
        for proposal_id, scenes in request.scene_proposal_previews.items():
            proposal = next((p for p in project.scene_proposals if p.id == proposal_id), None)
            if proposal is None or proposal.mode == "staging" or proposal.status != "ready":
                raise HTTPException(409, "Đề xuất đã đổi trạng thái; bản xem trước đang sửa vẫn được giữ.")
            ids = [s.id for s in scenes]
            if len(set(ids)) != len(ids) or not set(ids) <= {s.id for s in proposal.scenes}:
                raise HTTPException(422, "Bản xem trước phải giữ ID cảnh của đề xuất.")
            proposal.preview_scenes = scenes
        if request.scene_proposal_id is not None:
            if any(p.id == request.scene_proposal_id for p in project.staging_proposals):
                raise HTTPException(422, "Chọn từng ý dàn cảnh, không áp dụng cả lô.")
            if request.scene_proposal_id not in project.applicable_scene_proposal_ids or request.scene_outline is None:
                raise HTTPException(409, "Đề xuất đã dùng hoặc nguồn đã đổi. Bản đang sửa vẫn được giữ.")
            if any(getattr(request, key) != getattr(project, key)
                   for key in ("idea", "constraints", "answers", "draft", "response_language")):
                raise HTTPException(409, "Ý đồ hoặc story plan đã đổi; hãy lưu riêng và đối chiếu lại đề xuất.")
            proposal = next(p for p in project.scene_proposals if p.id == request.scene_proposal_id)
            if proposal.mode == "staging":
                raise HTTPException(422, "Chọn từng ý dàn cảnh, không áp dụng cả lô.")
            proposal.status = "applied"
            proposal.applied_revision = project.revision + 1
            ai_scene_fields = scene_fields(proposal.scenes)
        if "scene_outline" in request.model_fields_set:
            edit, outline = request.scene_outline, project.scene_outline
            if edit is None:
                if outline is not None:
                    raise HTTPException(422, "Không xóa nguồn dàn cảnh; bạn có thể bỏ từng cảnh.")
            elif outline is None:
                raise HTTPException(422, "Chọn nguồn story plan trước khi sửa dàn cảnh.")
            elif edit.id != outline.id or edit.version != outline.version:
                raise ProjectConflict
            elif edit.scenes != outline.scenes or confirmed:
                if checkpoint("scene_outline"):
                    archive_scene_outline(project)
                project.scene_outline = outline.model_copy(update={
                    "scenes": edit.scenes, "version": outline.version + 1,
                    "provenance": attribute_edits(outline.provenance, scene_fields(outline.scenes),
                        scene_fields(edit.scenes), ai_scene_fields, confirmed),
                })
        for proposal_id, scene in request.screenplay_proposal_previews.items():
            proposal = next((p for p in project.screenplay_proposals if p.id == proposal_id), None)
            if proposal is None or proposal.status != "ready" or proposal.scene is None:
                raise HTTPException(409, "Phương án đã đổi trạng thái; bản tự chỉnh vẫn giữ.")
            if (scene.id, scene.source_scene_id) != (proposal.scene.id, proposal.scene.source_scene_id):
                raise HTTPException(422, "Giữ ID cảnh đích của phương án.")
            proposal.preview_scene = scene
        if request.screenplay_proposal_id is not None:
            proposal = next((p for p in project.screenplay_proposals if p.id == request.screenplay_proposal_id), None)
            if proposal is None or proposal.id not in project.applicable_screenplay_proposal_ids or proposal.scene is None:
                raise HTTPException(409, "Phương án đã dùng/bỏ hoặc ngữ cảnh đã đổi; không nhận bản cũ.")
            expected = project.screenplay.model_copy(deep=True)
            replacement = proposal.preview_scene or proposal.scene
            expected.scenes = [replacement if s.id == proposal.target_scene_id else s for s in expected.scenes]
            if (request.screenplay is None or request.screenplay.model_dump() != expected.model_dump(include={"id", "version", "scenes"})
                    or any(getattr(request, key) != getattr(project, key) for key in ("idea", "constraints", "answers", "draft", "response_language"))
                    or (request.scene_outline is not None and request.scene_outline.model_dump() != project.scene_outline.model_dump(include={"id", "version", "scenes"}))
                    or request.scene_proposal_id is not None or request.staging_use is not None):
                raise HTTPException(409, "Dùng phương án chỉ thay đúng cảnh đã nêu. Giữ thành bản tự chỉnh nếu sửa các phần khác.")
            proposal.status, proposal.applied_revision = "applied", project.revision + 1
            ai_script_fields = scene_fields([proposal.scene], screenplay=True)
        if "screenplay" in request.model_fields_set:
            edit, current = request.screenplay, project.screenplay
            if edit is None:
                if current is not None:
                    raise HTTPException(422, "Không xóa bản kịch bản hoặc nguồn; hãy sửa nội dung từng khối.")
            elif current is None:
                raise HTTPException(422, "Chọn bản dàn cảnh đã lưu trước khi viết kịch bản.")
            elif edit.id != current.id or edit.version != current.version:
                raise ProjectConflict
            elif [(s.id, s.source_scene_id) for s in edit.scenes] != [(s.id, s.source_scene_id) for s in current.scenes]:
                raise HTTPException(422, "Giữ thứ tự và liên kết cảnh nguồn; thay cấu trúc ở phần Dàn cảnh rồi bắt đầu bản khác.")
            elif edit.scenes != current.scenes:
                owners = {b.id: s.id for s in current.scenes for b in s.blocks}
                if any(b.id in owners and owners[b.id] != s.id for s in edit.scenes for b in s.blocks):
                    raise HTTPException(422, "Không chuyển ID khối sang cảnh khác.")
                if checkpoint("screenplay"):
                    archive_screenplay(project)
                project.screenplay = current.model_copy(update={"scenes": edit.scenes, "version": current.version + 1,
                    "provenance": attribute_edits(current.provenance, scene_fields(current.scenes, True),
                        scene_fields(edit.scenes, True), ai_script_fields)})
        brief_changed = project.idea != request.idea or project.constraints != request.constraints
        if brief_changed:
            archive_clarifications(project, request.answers)
        language_changed = (
            "response_language" in request.model_fields_set
            and project.response_language != request.response_language
        )
        if project.draft != request.draft or language_changed:
            if checkpoint("draft"):
                add_version(project)
        restored = next((v for v in project.versions if v.id == request.restore_draft_id), None)
        if request.restore_draft_id and (restored is None or restored.draft != request.draft):
            raise HTTPException(409, "Bản khôi phục không khớp phiên bản đã lưu.")
        project.draft_provenance = (restored.draft_provenance.copy() if restored else
            attribute_edits(project.draft_provenance, draft_fields(project.draft), draft_fields(request.draft)))
        for key in ("title", "idea", "constraints", "draft"):
            setattr(project, key, getattr(request, key))
        if "response_language" in request.model_fields_set:
            project.response_language = request.response_language
        if brief_changed:
            project.analysis = None
            project.answers = []
            project.clarifications = {}
        else:
            project.answers = request.answers
        project.last_save_id = request.save_id
        project.last_save_revision = project.revision + 1 if request.save_id else None
        project.last_save_fingerprint = fingerprint if request.save_id else None
        return save_project(project, "autosaving" if request.save_mode == "autosave" and not boundary else "saving")


def archive_screenplay(project: ProjectResponse) -> None:
    if project.screenplay is not None:
        project.screenplay_versions.append(ScreenplayVersion(
            id=str(uuid4()), created_at=datetime.now(UTC).isoformat(),
            screenplay=project.screenplay.model_copy(deep=True)))


def archive_scene_outline(project: ProjectResponse) -> None:
    if project.scene_outline is not None:
        project.scene_versions.append(SceneOutlineVersion(
            id=str(uuid4()), created_at=datetime.now(UTC).isoformat(),
            outline=project.scene_outline.model_copy(deep=True),
        ))


@router.post("/{project_id}/scene-outline", response_model=ProjectResponse)
def start_scene_outline(project_id: str, request: StartSceneOutline):
    with project_errors():
        project = load_project(project_id, request.revision)
        if project.scene_outline is not None:
            raise HTTPException(409, "Dự án đã có dàn cảnh. Bản hiện tại được giữ nguyên.")
        if request.source_version_id == "current":
            draft, context, language = project.draft, project.author_context, project.response_language
        else:
            version = next((v for v in project.versions if v.id == request.source_version_id), None)
            if version is None:
                raise HTTPException(404, "Không tìm thấy phiên bản story plan đã chọn.")
            draft, language = version.draft, version.response_language
            choices = {**version.clarifications, **dict(zip(version.questions, version.answers))}
            context = author_context(version.idea, version.constraints,
                                     ((q, a) for q, a in choices.items() if a.strip()),
                                     version.questions, version.answers)
        if draft is None:
            raise HTTPException(422, "Cần một bản story plan đã lưu để bắt đầu dàn cảnh.")
        project.scene_outline = SceneOutline(
            id=str(uuid4()), version=1, scenes=[], source=ScenePlanSource(
                id=str(uuid4()), project_revision=project.revision,
                version_id=request.source_version_id, draft=draft.model_copy(deep=True),
                context=context.model_copy(deep=True), response_language=language,
                draft_provenance=(project.draft_provenance.copy() if request.source_version_id == "current"
                                  else version.draft_provenance.copy()),
            ),
        )
        return save_project(project)


@router.post("/{project_id}/scene-versions/{version_id}/restore", response_model=ProjectResponse)
def restore_scene_outline(project_id: str, version_id: str, request: RevisionRequest):
    with project_errors():
        project = load_project(project_id, request.revision)
        version = next((v for v in project.scene_versions if v.id == version_id), None)
        if project.scene_outline is None or version is None:
            raise HTTPException(404, "Không tìm thấy bản dàn cảnh đã lưu.")
        current_version = project.scene_outline.version
        archive_scene_outline(project)
        project.scene_outline = version.outline.model_copy(deep=True, update={
            "version": current_version + 1,
        })
        return save_project(project)


def get_scene_provider():
    return create_provider()


@router.post("/{project_id}/scene-suggestions", response_model=ProjectResponse)
def scene_suggestions(project_id: str, request: SceneSuggestionRequest):
    with project_errors():
        with progress_step("scene_source"):
            project = load_project(project_id)
            pool_name = "staging_proposals" if request.mode == "staging" else "scene_proposals"
            pool = getattr(project, pool_name)
            existing = next((p for p in [*project.scene_proposals, *project.staging_proposals] if p.id == request.request_id), None)
            if existing:
                if (existing.mode, existing.target_scene_id, existing.instructions) != (
                    request.mode, request.target_scene_id, request.instructions
                ):
                    raise HTTPException(409, "ID tác vụ đã được dùng cho yêu cầu khác.")
                return project
            if request.revision != project.revision:
                raise ProjectConflict
            outline = project.scene_outline
            if outline is None:
                raise HTTPException(422, "Chọn nguồn story plan trước khi nhận gợi ý cảnh.")
            if request.mode == "list" and (outline.scenes or request.target_scene_id is not None):
                raise HTTPException(422, "Chỉ gợi ý danh sách ban đầu khi dàn cảnh chưa có cảnh.")
            if request.mode == "append" and len(outline.scenes) >= 60:
                raise HTTPException(422, "Dàn cảnh đã có tối đa 60 cảnh.")
            if (request.target_scene_id is not None or request.mode in {"develop", "staging"}) and not any(
                s.id == request.target_scene_id for s in outline.scenes
            ):
                raise HTTPException(422, "Không tìm thấy cảnh đích trong bản nguồn.")
            if any(p.status == "pending" for p in [*project.scene_proposals, *project.staging_proposals]):
                raise HTTPException(409, "Đang có yêu cầu chưa rõ kết quả; mở lại đề xuất, không tự chạy thêm.")
            proposal = SceneProposal(
                id=request.request_id, created_at=datetime.now(UTC).isoformat(),
                prompt_version=STAGING_PROMPT_VERSION if request.mode == "staging" else PROMPT_VERSION,
                source_revision=project.revision, source_content=project.content_key(),
                source_outline=outline.model_copy(deep=True), mode=request.mode,
                target_scene_id=request.target_scene_id, instructions=request.instructions,
            )
            pool.append(proposal)
            project = save_project(project, "scene_checkpoint")

        def keep_result(raw):
            # This transaction changes only the proposal; concurrent author edits stay intact.
            for index, item in enumerate(raw.get(pool_name, [])):
                if item["id"] == proposal.id and item["status"] in {"pending", "discarded"}:
                    stored = proposal.model_copy(update={"status": "discarded"}) if item["status"] == "discarded" else proposal
                    raw[pool_name][index] = stored.model_dump(mode="json")
                    break

        try:
            with capture_workflow("scene_suggestions", {"id": project.id, "revision": project.revision,
                                                       "proposal": proposal.model_dump(mode="json")}) as dataset:
                provider = recording_provider(get_scene_provider())
                metadata = provider.metadata
                proposal.provider, proposal.model, proposal.parameters = metadata.provider, metadata.model, metadata.parameters
                proposal = (suggest_staging(proposal, provider) if request.mode == "staging"
                            else suggest_scenes(proposal, provider))
                with progress_step("scene_proposal_save"):
                    project = ProjectResponse.model_validate(get_project_store().update(project_id, keep_result))
                stored = next(p for p in getattr(project, pool_name) if p.id == proposal.id)
                dataset.complete({"id": project.id, "revision": project.revision,
                                  "proposal": stored.model_dump(mode="json")}, workflow_complete=False)
        except Exception as error:
            proposal.status = "failed"
            proposal.error = type(error).__name__
            get_project_store().update(project_id, keep_result)
            raise
        return project


@router.post("/{project_id}/scene-proposals/{proposal_id}/discard", response_model=ProjectResponse)
def discard_scene_proposal(project_id: str, proposal_id: str, request: RevisionRequest):
    with project_errors():
        project = load_project(project_id, request.revision)
        proposal = next((p for p in [*project.scene_proposals, *project.staging_proposals] if p.id == proposal_id), None)
        if proposal is None:
            raise HTTPException(404, "Không tìm thấy đề xuất cảnh.")
        if proposal.status != "applied":
            proposal.status = "discarded"
        return save_project(project)


@router.post("/{project_id}/scene-proposals/{proposal_id}/ideas/{idea_id}/discard", response_model=ProjectResponse)
def discard_staging_idea(project_id: str, proposal_id: str, idea_id: str, request: RevisionRequest):
    with project_errors():
        project = load_project(project_id, request.revision)
        proposal = next((p for p in project.staging_proposals if p.id == proposal_id and p.mode == "staging"), None)
        idea = next((i for i in proposal.staging_ideas if i.id == idea_id), None) if proposal else None
        if idea is None:
            raise HTTPException(404, "Không tìm thấy ý góp ý trong bản nguồn này.")
        if idea.status == "applied":
            raise HTTPException(409, "Ý đã dùng được giữ trong lịch sử; không đổi thành đã bỏ.")
        idea.status = "discarded"
        return save_project(project)


@router.post("/{project_id}/analyze", response_model=ProjectResponse)
def analyze_project(project_id: str, request: RevisionRequest):
    return _analyze_project(project_id, request)


@router.post("/{project_id}/clarify", response_model=ProjectResponse)
def clarify_project(project_id: str, request: RevisionRequest):
    return _analyze_project(project_id, request, conversation=True)


def _analyze_project(project_id: str, request: RevisionRequest, conversation: bool = False):
    with project_errors():
        project = load_project(project_id, request.revision)
        if not project.idea.strip():
            raise HTTPException(422, "Hãy nhập ý tưởng trước khi bắt đầu.")
        existing = list(project.analysis.missing_information) if conversation and project.analysis else []
        if len(existing) >= MAX_CHOICES:
            raise HTTPException(422, "Đã có đủ 20 lượt làm rõ. Bạn có thể sửa các lựa chọn trước khi xác nhận.")
        with capture_workflow("analyze", dataset_snapshot(project)) as dataset:
            known_answers = project.creator_answers()
            reasoning = get_story_generation_service().analyze(
                project.idea, constraints_for(project), answers=known_answers,
                response_language=project.response_language,
            )
            previous_answers = dict(known_answers)
            archive_clarifications(project)
            project.clarifications = previous_answers
            project.analysis = AnalysisResponse(
                artifact_id=reasoning.metadata.artifact_id,
                ai_suggestions=list(getattr(reasoning, "ai_suggestions", ())),
                summary=next(
                    (note.content for note in reasoning.notes if note.label == "Analysis summary"), ""
                ),
                notes=[
                    AnalysisNoteResponse(label=note.label, content=note.content)
                    for note in reasoning.notes
                ],
                missing_information=conversation_questions(reasoning.open_questions, existing, previous_answers,
                    resolve_response_language(project.idea, project.response_language)) if conversation else list(reasoning.open_questions[:3]),
            )
            project.answers = [
                previous_answers.get(question, "") for question in project.analysis.missing_information
            ]
            saved = save_project(project)
            dataset.complete(dataset_snapshot(saved))
            return saved


@router.post("/{project_id}/plan", response_model=ProjectResponse)
def plan_project(project_id: str, request: RevisionRequest):
    with project_errors():
        project = load_project(project_id, request.revision)
        with progress_step("plan_choices"):
            if project.analysis is None:
                raise HTTPException(422, "Hãy làm rõ ý tưởng trước khi tạo bản phát triển.")
            questions = project.analysis.missing_information
            if len(questions) != len(project.answers):
                raise HTTPException(422, "Câu trả lời phải khớp với bộ câu hỏi hiện tại.")
        generation_id = None

        def keep_plan(plan: StoryPlanArtifact) -> None:
            nonlocal project, generation_id
            generation = PlanGeneration(
                id=plan.metadata.artifact_id, created_at=datetime.now(UTC).isoformat(),
                source_revision=project.revision, source_content=project.content_key(),
                context=project.author_context,
                draft=StoryDraft(
                    title=plan.title or "Phim ngắn chưa đặt tên", logline=plan.logline or "",
                    sections=[{"title": section.title, "purpose": section.purpose,
                               "content": section.content} for section in plan.sections],
                ),
            )
            if project.draft is None:
                project.draft = generation.draft.model_copy(deep=True)
                project.draft_provenance = ai_draft(generation.draft)
                project.feedback = project.feedback_source = project.reviewed_content = None
                generation.applied_revision = project.revision + 1
            project.plan_generations.append(generation)
            project = save_project(project, "plan_checkpoint")
            generation_id = generation.id

        try:
            with capture_workflow("plan", dataset_snapshot(project)) as dataset:
                run = get_story_generation_service().plan(
                    project.idea, project.creator_answers(), constraints_for(project),
                    response_language=project.response_language, on_planned=keep_plan,
                    structured_review=True,
                    pending_questions=tuple(q for q, a in zip(questions, project.answers) if not a.strip()),
                )
                generation = project.plan_generations[-1]
                generation.feedback = _to_response(run).evaluation
                generation.critic_status = "reviewed"
                # A proposal's critic reads its draft, never the working draft it may replace.
                reviewed = project.model_copy(deep=True)
                reviewed.draft = generation.draft.model_copy(deep=True)
                reviewed.feedback = generation.feedback
                attach_feedback_source(reviewed, generation.context)
                generation.feedback_source = reviewed.feedback_source
                if generation.applied_revision is not None:
                    project.feedback = reviewed.feedback
                    project.feedback_source = reviewed.feedback_source
                    project.reviewed_content = reviewed.reviewed_content
                    add_version(project)
                project = save_project(project, "plan_save")
                dataset.complete(
                    {**dataset_snapshot(project), "plan_generation": generation.model_dump(mode="json")},
                    workflow_complete=generation.applied_revision is not None,
                )
        except ProviderError:
            if generation_id is None:
                raise
            project.plan_generations[-1].critic_status = "failed"
            # Use only the checkpoint revision: a late critic must not overwrite a newer save.
            project = save_project(project, "plan_save")
        return project


@router.post("/{project_id}/plans/{generation_id}/accept", response_model=ProjectResponse)
def accept_plan(project_id: str, generation_id: str, request: RevisionRequest):
    with project_errors():
        project = load_project(project_id, request.revision)
        generation = next((item for item in project.plan_generations if item.id == generation_id), None)
        if generation is None:
            raise HTTPException(404, "Không tìm thấy bản đề xuất trong dự án này.")
        if generation.id not in project.applicable_plan_ids:
            raise HTTPException(
                409, "Bản đề xuất đã được nhận hoặc nguồn đã thay đổi. Bản đang viết vẫn được giữ.",
            )
        add_version(project)
        project.draft = generation.draft.model_copy(deep=True)
        project.draft_provenance = ai_draft(generation.draft)
        source = generation.feedback_source
        project.feedback = generation.feedback if source is not None else None
        project.feedback_source = source.model_copy(deep=True) if source is not None else None
        project.reviewed_content = source.content_key if source is not None else None
        generation.applied_revision = project.revision + 1
        add_version(project)
        return save_project(project)


@router.post("/{project_id}/review", response_model=ProjectResponse)
def review_project(project_id: str, request: RevisionRequest):
    with project_errors():
        project = load_project(project_id, request.revision)
        if project.draft is None:
            raise HTTPException(422, "Chưa có bản phát triển để nhận phản hồi.")
        if not any(section.content.strip() for section in project.draft.sections):
            raise HTTPException(422, "Hãy viết ít nhất một phần trước khi nhận phản hồi.")
        with capture_workflow("review", dataset_snapshot(project)) as dataset:
            context = project.author_context
            previous_draft = project.feedback_source.draft if project.feedback_source else None
            if previous_draft == project.draft:
                previous_draft = next((version.draft for version in reversed(project.versions)
                                       if version.draft != project.draft), None)
            evaluation = get_story_generation_service().review(
                project.idea,
                project.draft.title,
                project.draft.logline,
                tuple(
                    PlanSection(
                        section_id=f"section-{i}",
                        title=section.title,
                        purpose=section.purpose,
                        content=section.content,
                    )
                    for i, section in enumerate(project.draft.sections)
                ),
                json.dumps(context.ai_context(), ensure_ascii=False),
                response_language=project.response_language,
                review_context=review_context(
                    project.draft.model_dump(),
                    previous_draft.model_dump() if previous_draft else None,
                    context.model_dump(),
                    resolve_response_language(project.idea, project.response_language) == "Vietnamese",
                ),
            )
            project.feedback = EvaluationResponse(
                artifact_id=evaluation.metadata.artifact_id,
                revision_notes=evaluation.revision_notes,
                passed=evaluation.passed,
                rubric_scores={
                    item.criterion_id: item.score
                    for item in evaluation.findings
                    if item.score is not None
                },
                findings=[item.__dict__ for item in evaluation.findings],
            )
            attach_feedback_source(project, context)
            add_version(project)
            saved = save_project(project)
            dataset.complete(dataset_snapshot(saved))
            return saved
