from pydantic import BaseModel, ConfigDict, Field

from app.application.workflow import DEFAULT_DOMAIN_ID


class IdeaRequest(BaseModel):
    """Transport contract for submitting an early creative idea."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    domain_id: str = Field(default=DEFAULT_DOMAIN_ID, min_length=1, max_length=120)
    idea: str = Field(min_length=1, max_length=5000)
    constraints: list[str] = Field(default_factory=list, max_length=20)


class AnalysisNoteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    label: str
    content: str


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    artifact_id: str
    summary: str
    notes: list[AnalysisNoteResponse] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)


class StoryPlanSectionResponse(BaseModel):
    """Transport shape for a story plan section."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str
    purpose: str
    content: str


class StoryPlanResponse(BaseModel):
    """Transport response for a future story planning endpoint."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    request_id: str
    domain_id: str
    title: str | None = None
    logline: str | None = None
    sections: list[StoryPlanSectionResponse] = Field(default_factory=list)


class EvaluationFindingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    criterion_id: str
    message: str
    severity: str
    score: int | None = None


class EvaluationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    artifact_id: str
    passed: bool | None = None
    rubric_scores: dict[str, int] = Field(default_factory=dict)
    findings: list[EvaluationFindingResponse] = Field(default_factory=list)


class GenerateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    analysis: AnalysisResponse
    story_plan: StoryPlanResponse
    evaluation: EvaluationResponse
