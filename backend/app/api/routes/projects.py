import asyncio
import json
import logging
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
)
from app.api.schemas.story import AnalysisNoteResponse, AnalysisResponse, EvaluationResponse
from app.application.ai_provider import (
    MalformedProviderResponseError,
    MissingProviderConfigurationError,
    ProviderRequestError,
    ProviderTimeoutError,
    ProviderError,
)
from app.application.dataset import capture_workflow
from app.application.clarification import MAX_CHOICES, conversation_questions
from app.application.language import LanguageSelectionRequired, resolve_response_language
from app.application.progress import progress_listener, report_progress, progress_step
from app.application.project_store import ProjectConflict, ProjectNotFound, ProjectStore
from app.application.revision_review import review_context
from app.core.artifacts import Constraint, PlanSection, StoryPlanArtifact

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("/{project_id}/{operation}/stream")
async def stream_project_operation(
    project_id: str, operation: Literal["analyze", "clarify", "plan", "review"], request: RevisionRequest
):
    events: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def work():
        def publish(event):
            loop.call_soon_threadsafe(events.put_nowait, event)

        token = progress_listener.set(publish)
        try:
            handler = {"analyze": analyze_project, "clarify": clarify_project, "plan": plan_project, "review": review_project}
            result = handler[operation](project_id, request)
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
        data = project.model_dump(exclude_computed_fields=True)
        return ProjectResponse.model_validate(get_project_store().save(data, project.revision))


def dataset_snapshot(project: ProjectResponse) -> dict[str, object]:
    return project.model_dump(mode="json", exclude={
        "versions", "clarification_history", "plan_generations", "applicable_plan_ids",
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
        project = load_project(project_id, request.revision)
        questions = project.analysis.missing_information if project.analysis else []
        if len(request.answers) != len(questions):
            raise HTTPException(422, "Câu trả lời phải khớp với bộ câu hỏi hiện tại.")
        brief_changed = project.idea != request.idea or project.constraints != request.constraints
        if brief_changed:
            archive_clarifications(project, request.answers)
        language_changed = (
            "response_language" in request.model_fields_set
            and project.response_language != request.response_language
        )
        if project.draft != request.draft or language_changed:
            add_version(project)
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
        if existing and (len(project.answers) != len(existing) or any(not answer.strip() for answer in project.answers)):
            raise HTTPException(422, "Hãy trả lời hoặc để quyết định sau các câu hiện tại trước khi hỏi tiếp.")
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
            if len(questions) != len(project.answers) or any(
                not answer.strip() for answer in project.answers
            ):
                raise HTTPException(422, "Hãy trả lời hoặc chọn để quyết định sau cho từng câu hỏi.")
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
