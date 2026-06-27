from fastapi import APIRouter, HTTPException, status

from app.api.schemas import (
    AnalysisNoteResponse,
    AnalysisResponse,
    EvaluationFindingResponse,
    EvaluationResponse,
    GenerateResponse,
    IdeaRequest,
    StoryPlanResponse,
    StoryPlanSectionResponse,
)
from app.application.workflow import HarnessRun, create_story_generation_service
from app.core.artifacts import Constraint
from app.infrastructure.openai_provider import (
    MalformedProviderResponseError,
    MissingProviderConfigurationError,
    ProviderRequestError,
    ProviderTimeoutError,
)


router = APIRouter(prefix="/api", tags=["generation"])


@router.post("/generate", response_model=GenerateResponse)
def generate(request: IdeaRequest) -> GenerateResponse:
    try:
        run = get_story_generation_service().generate(
            idea_text=request.idea,
            domain_id=request.domain_id,
            constraints=tuple(
                Constraint(name=f"constraint-{index + 1}", value=constraint)
                for index, constraint in enumerate(request.constraints)
            ),
        )
    except MissingProviderConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI provider is not configured.",
        ) from error
    except ProviderTimeoutError as error:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI provider timed out.",
        ) from error
    except (ProviderRequestError, MalformedProviderResponseError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider failed to generate a structured response.",
        ) from error
    return _to_response(run)


def get_story_generation_service():
    return create_story_generation_service()


def _to_response(run: HarnessRun) -> GenerateResponse:
    return GenerateResponse(
        analysis=AnalysisResponse(
            artifact_id=run.analysis.metadata.artifact_id,
            summary=_analysis_summary(run),
            notes=[
                AnalysisNoteResponse(label=note.label, content=note.content)
                for note in run.analysis.notes
            ],
            missing_information=list(run.analysis.open_questions),
        ),
        story_plan=StoryPlanResponse(
            request_id=run.story_plan.metadata.artifact_id,
            domain_id=run.story_plan.metadata.domain_id,
            title=run.story_plan.title,
            logline=run.story_plan.logline,
            sections=[
                StoryPlanSectionResponse(
                    title=section.title,
                    purpose=section.purpose,
                    content=section.content,
                )
                for section in run.story_plan.sections
            ],
        ),
        evaluation=EvaluationResponse(
            artifact_id=run.evaluation.metadata.artifact_id,
            passed=run.evaluation.passed,
            rubric_scores={
                finding.criterion_id: finding.score
                for finding in run.evaluation.findings
                if finding.score is not None
            },
            findings=[
                EvaluationFindingResponse(
                    criterion_id=finding.criterion_id,
                    message=finding.message,
                    severity=finding.severity,
                    score=finding.score,
                )
                for finding in run.evaluation.findings
            ],
        ),
    )


def _analysis_summary(run: HarnessRun) -> str:
    missing_count = len(run.analysis.open_questions)
    return (
        "The idea has enough signal for a first short-film story plan, "
        f"with {missing_count} missing decisions to clarify in the next pass."
    )
