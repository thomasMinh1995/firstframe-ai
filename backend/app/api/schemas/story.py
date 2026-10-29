from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from app.application.language import ResponseLanguage
from app.application.workflow import DEFAULT_DOMAIN_ID


class IdeaRequest(BaseModel):
    """Transport contract for submitting an early creative idea."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    domain_id: str = Field(default=DEFAULT_DOMAIN_ID, min_length=1, max_length=120)
    idea: str = Field(min_length=1, max_length=5000)
    constraints: list[str] = Field(default_factory=list, max_length=20)
    response_language: ResponseLanguage = "auto"


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
    ai_suggestions: list[str] = Field(default_factory=list, max_length=3)


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


class RevisionTargetResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    target_id: str
    quote: str


class RevisionNoteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    note_id: str
    artifact_id: str
    comparison: Literal["uncertain", "mismatch"]
    observation: str = Field(min_length=1)
    suggestion: str
    decision_id: str
    decision_quote: str
    decision_question: str | None
    targets: list[RevisionTargetResponse] = Field(min_length=1, max_length=2)

    @model_validator(mode="after")
    def mismatch_needs_next_step(self):
        if self.comparison == "mismatch" and not self.suggestion.strip():
            raise ValueError("A mismatch needs a specific next step.")
        return self


class EvaluationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    artifact_id: str
    passed: bool | None = None
    rubric_scores: dict[str, int] = Field(default_factory=dict)
    findings: list[EvaluationFindingResponse] = Field(default_factory=list)
    revision_notes: list[RevisionNoteResponse] | None = None

    @field_validator("revision_notes", mode="before")
    @classmethod
    def readable_legacy_feedback(cls, value):
        if value is None:
            return None
        try:
            if not isinstance(value, (list, tuple)) or len(value) > 3:
                return None
            notes = [RevisionNoteResponse.model_validate(item) for item in value]
            if len({item.note_id for item in notes}) != len(notes):
                return None
            return notes
        except ValidationError:
            # Broken optional metadata must not prevent opening an older project.
            return None


class GenerateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    analysis: AnalysisResponse
    story_plan: StoryPlanResponse
    evaluation: EvaluationResponse
