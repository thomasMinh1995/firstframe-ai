import json
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.api.routes.generate import _to_response, get_story_generation_service
from app.api.schemas.projects import (
    ClarificationVersion,
    DraftVersion,
    ProjectResponse,
    ProjectSummary,
    ProjectUpdate,
    RevisionRequest,
    StoryDraft,
)
from app.api.schemas.story import AnalysisNoteResponse, AnalysisResponse, EvaluationResponse
from app.application.project_store import ProjectConflict, ProjectNotFound, ProjectStore
from app.core.artifacts import Constraint, PlanSection
from app.infrastructure.openai_provider import (
    MalformedProviderResponseError,
    MissingProviderConfigurationError,
    ProviderRequestError,
    ProviderTimeoutError,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


def get_project_store() -> ProjectStore:
    return ProjectStore(Path(__file__).resolve().parents[3] / ".data" / "projects.sqlite3")


@contextmanager
def project_errors():
    try:
        yield
    except ProjectNotFound as error:
        raise HTTPException(404, "Project not found.") from error
    except ProjectConflict as error:
        raise HTTPException(
            409, "Dự án đã thay đổi ở cửa sổ khác. Hãy tải bản sao trước khi mở lại dự án."
        ) from error
    except MissingProviderConfigurationError as error:
        raise HTTPException(503, "Chưa cấu hình OPENAI_API_KEY cho backend.") from error
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


def save_project(project: ProjectResponse) -> ProjectResponse:
    data = project.model_dump(exclude={"feedback_is_current"})
    return ProjectResponse.model_validate(get_project_store().save(data, project.revision))


def constraints_for(project: ProjectResponse) -> tuple[Constraint, ...]:
    return tuple(
        Constraint(name=f"constraint-{i}", value=value)
        for i, value in enumerate(project.constraints)
    )


def add_version(project: ProjectResponse) -> None:
    if project.draft is not None:
        version = DraftVersion(
            id=str(uuid4()),
            created_at=datetime.now(UTC).isoformat(),
            idea=project.idea,
            constraints=project.constraints,
            questions=project.analysis.missing_information if project.analysis else [],
            answers=project.answers,
            draft=project.draft.model_copy(deep=True),
            feedback=project.feedback if project.feedback_is_current else None,
        )
        if project.versions and project.versions[-1].model_dump(
            exclude={"id", "created_at"}
        ) == version.model_dump(exclude={"id", "created_at"}):
            return
        project.versions.append(version)


def archive_clarifications(project: ProjectResponse, answers: list[str] | None = None) -> None:
    answers = project.answers if answers is None else answers
    if project.analysis is None or not any(answer.strip() for answer in answers):
        return
    version = ClarificationVersion(
        id=str(uuid4()),
        created_at=datetime.now(UTC).isoformat(),
        idea=project.idea,
        constraints=project.constraints,
        questions=project.analysis.missing_information,
        answers=answers,
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
    return get_project_store().create(project.model_dump(exclude={"feedback_is_current"}))


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
        if project.draft != request.draft:
            add_version(project)
        for key in ("title", "idea", "constraints", "draft"):
            setattr(project, key, getattr(request, key))
        if brief_changed:
            project.analysis = None
            project.answers = []
        else:
            project.answers = request.answers
        return save_project(project)


@router.post("/{project_id}/analyze", response_model=ProjectResponse)
def analyze_project(project_id: str, request: RevisionRequest):
    with project_errors():
        project = load_project(project_id, request.revision)
        if not project.idea.strip():
            raise HTTPException(422, "Hãy nhập ý tưởng trước khi bắt đầu.")
        reasoning = get_story_generation_service().analyze(project.idea, constraints_for(project))
        previous_answers = dict(
            zip(project.analysis.missing_information if project.analysis else [], project.answers)
        )
        archive_clarifications(project)
        project.analysis = AnalysisResponse(
            artifact_id=reasoning.metadata.artifact_id,
            summary=next(
                (note.content for note in reasoning.notes if note.label == "Analysis summary"), ""
            ),
            notes=[
                AnalysisNoteResponse(label=note.label, content=note.content)
                for note in reasoning.notes
            ],
            missing_information=list(reasoning.open_questions[:3]),
        )
        project.answers = [
            previous_answers.get(question, "") for question in project.analysis.missing_information
        ]
        return save_project(project)


@router.post("/{project_id}/plan", response_model=ProjectResponse)
def plan_project(project_id: str, request: RevisionRequest):
    with project_errors():
        project = load_project(project_id, request.revision)
        if project.analysis is None:
            raise HTTPException(422, "Hãy làm rõ ý tưởng trước khi tạo story plan.")
        questions = project.analysis.missing_information
        if len(questions) != len(project.answers) or any(
            not answer.strip() for answer in project.answers
        ):
            raise HTTPException(422, "Hãy trả lời hoặc chọn để quyết định sau cho từng câu hỏi.")
        run = get_story_generation_service().plan(
            project.idea, tuple(zip(questions, project.answers)), constraints_for(project)
        )
        generated = _to_response(run)
        add_version(project)
        project.draft = StoryDraft(
            title=generated.story_plan.title or "Phim ngắn chưa đặt tên",
            logline=generated.story_plan.logline or "",
            sections=[section.model_dump() for section in generated.story_plan.sections],
        )
        project.feedback = generated.evaluation
        project.reviewed_content = project.content_key()
        add_version(project)
        return save_project(project)


@router.post("/{project_id}/review", response_model=ProjectResponse)
def review_project(project_id: str, request: RevisionRequest):
    with project_errors():
        project = load_project(project_id, request.revision)
        if project.draft is None:
            raise HTTPException(422, "Chưa có story plan để nhận phản hồi.")
        if not any(section.content.strip() for section in project.draft.sections):
            raise HTTPException(422, "Hãy viết ít nhất một phần trước khi nhận phản hồi.")
        context = {
            "idea": project.idea,
            "constraints": project.constraints,
            "clarifications": [
                {"question": question, "answer": answer}
                for question, answer in zip(
                    project.analysis.missing_information if project.analysis else [],
                    project.answers,
                )
            ],
        }
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
            json.dumps(context, ensure_ascii=False),
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
        project.reviewed_content = project.content_key()
        add_version(project)
        return save_project(project)
