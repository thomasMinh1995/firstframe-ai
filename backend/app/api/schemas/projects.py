import json
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.api.schemas.story import AnalysisResponse, EvaluationResponse

ShortText = Annotated[str, Field(max_length=2000)]


class DraftSection(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200)
    purpose: str = Field(max_length=2000)
    content: str = Field(max_length=10000)


class StoryDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(max_length=200)
    logline: str = Field(max_length=2000)
    sections: list[DraftSection] = Field(min_length=1, max_length=20)


class RevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision: int = Field(ge=0)


class ProjectUpdate(RevisionRequest):
    title: str = Field(min_length=1, max_length=200)
    idea: str = Field(max_length=5000)
    constraints: list[ShortText] = Field(max_length=20)
    answers: list[ShortText] = Field(max_length=3)
    draft: StoryDraft | None


class ClarificationVersion(BaseModel):
    id: str
    created_at: str
    idea: str
    constraints: list[str]
    questions: list[str] = Field(default_factory=list)
    answers: list[str]
    clarifications: dict[str, str] = Field(default_factory=dict)


class DraftVersion(ClarificationVersion):
    draft: StoryDraft
    feedback: EvaluationResponse | None = None


class ProjectResponse(BaseModel):
    id: str
    revision: int = 0
    updated_at: str
    title: str = "Dự án chưa đặt tên"
    idea: str = ""
    constraints: list[str] = Field(default_factory=list)
    analysis: AnalysisResponse | None = None
    answers: list[str] = Field(default_factory=list)
    clarifications: dict[str, str] = Field(default_factory=dict)
    draft: StoryDraft | None = None
    feedback: EvaluationResponse | None = None
    reviewed_content: str | None = None
    versions: list[DraftVersion] = Field(default_factory=list)
    clarification_history: list[ClarificationVersion] = Field(default_factory=list)

    def creator_answers(self, answers: list[str] | None = None) -> tuple[tuple[str, str], ...]:
        questions = self.analysis.missing_information if self.analysis else []
        current = dict(zip(questions, self.answers if answers is None else answers))
        combined = {**self.clarifications, **current}
        return tuple((question, answer) for question, answer in combined.items() if answer.strip())

    def content_key(self) -> str:
        return json.dumps(
            {
                "idea": self.idea,
                "constraints": self.constraints,
                "answers": self.answers,
                "questions": self.analysis.missing_information if self.analysis else [],
                "clarifications": dict(self.creator_answers()),
                "draft": self.draft.model_dump() if self.draft else None,
            },
            ensure_ascii=False,
            sort_keys=True,
        )

    @computed_field
    @property
    def feedback_is_current(self) -> bool:
        return self.feedback is not None and self.reviewed_content == self.content_key()


class ProjectSummary(BaseModel):
    id: str
    title: str
    updated_at: str
