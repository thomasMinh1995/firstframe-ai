import json
from collections.abc import Iterable
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    computed_field,
    field_validator,
    model_validator,
)

from app.api.schemas.story import AnalysisResponse, EvaluationResponse
from app.application.language import ResponseLanguage

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
    response_language: ResponseLanguage = "auto"
    title: str = Field(min_length=1, max_length=200)
    idea: str = Field(max_length=5000)
    constraints: list[ShortText] = Field(max_length=20)
    answers: list[ShortText] = Field(max_length=3)
    draft: StoryDraft | None


class AuthorAnswer(BaseModel):
    question: str
    answer: str
    input_index: int | None = None


class PendingQuestion(BaseModel):
    question: str
    input_index: int


class AuthorContext(BaseModel):
    idea: str
    constraints: list[str]
    clarifications: list[AuthorAnswer]
    pending_questions: list[PendingQuestion]

    def ai_context(self) -> dict[str, object]:
        return {
            "idea": self.idea,
            "constraints": self.constraints,
            "clarifications": [item.model_dump(exclude={"input_index"}) for item in self.clarifications],
        }


def author_context(
    idea: str, constraints: list[str], choices: Iterable[tuple[str, str]],
    questions: list[str], answers: list[str],
) -> AuthorContext:
    indices = {question: i for i, question in enumerate(questions)}
    return AuthorContext(
        idea=idea, constraints=constraints,
        clarifications=[AuthorAnswer(question=q, answer=a, input_index=indices.get(q)) for q, a in choices],
        pending_questions=[PendingQuestion(question=q, input_index=i)
                           for i, q in enumerate(questions) if i >= len(answers) or not answers[i].strip()],
    )


class ReviewedContent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    response_language: ResponseLanguage = "auto"
    idea: str
    constraints: list[str]
    questions: list[str]
    answers: list[str]
    clarifications: dict[str, str]
    draft: StoryDraft


class FeedbackSource(BaseModel):
    project_id: str
    artifact_id: str
    revision: int = Field(ge=0)
    content_key: str
    context: AuthorContext
    draft: StoryDraft

    def matches(self, feedback: EvaluationResponse | None) -> bool:
        if feedback is None or self.artifact_id != feedback.artifact_id:
            return False
        try:
            snapshot = ReviewedContent.model_validate_json(self.content_key)
        except ValidationError:
            return False
        expected = author_context(snapshot.idea, snapshot.constraints,
                                  snapshot.clarifications.items(), snapshot.questions, snapshot.answers)
        return (self.draft == snapshot.draft
                and len({item.question for item in self.context.clarifications}) == len(self.context.clarifications)
                and self.context.idea == expected.idea
                and self.context.constraints == expected.constraints
                and self.context.pending_questions == expected.pending_questions
                and {item.question: item for item in self.context.clarifications}
                == {item.question: item for item in expected.clarifications})


def parse_feedback_source(value: object) -> FeedbackSource | None:
    try:
        return FeedbackSource.model_validate(value) if value is not None else None
    except ValidationError:
        return None


class ClarificationVersion(BaseModel):
    response_language: ResponseLanguage = "auto"
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
    feedback_source: FeedbackSource | None = None

    _parse_source = field_validator("feedback_source", mode="before")(parse_feedback_source)

    @model_validator(mode="after")
    def check_source(self) -> "DraftVersion":
        source = self.feedback_source
        if source and (not source.matches(self.feedback) or source.draft != self.draft
                       or source.context.idea != self.idea or source.context.constraints != self.constraints
                       or {item.question: item.answer for item in source.context.clarifications}
                       != self.clarifications):
            self.feedback_source = None
        return self


class ProjectResponse(BaseModel):
    response_language: ResponseLanguage = "auto"
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
    feedback_source: FeedbackSource | None = None
    reviewed_content: str | None = None
    versions: list[DraftVersion] = Field(default_factory=list)
    clarification_history: list[ClarificationVersion] = Field(default_factory=list)

    _parse_source = field_validator("feedback_source", mode="before")(parse_feedback_source)

    @model_validator(mode="after")
    def check_sources(self) -> "ProjectResponse":
        source = self.feedback_source
        if source and (not source.matches(self.feedback) or source.project_id != self.id
                       or source.content_key != self.reviewed_content or source.revision > self.revision):
            self.feedback_source = None
        for version in self.versions:
            if version.feedback_source and (version.feedback_source.project_id != self.id
                                            or version.feedback_source.revision > self.revision):
                version.feedback_source = None
        return self

    def creator_answers(self, answers: list[str] | None = None) -> tuple[tuple[str, str], ...]:
        questions = self.analysis.missing_information if self.analysis else []
        current = dict(zip(questions, self.answers if answers is None else answers))
        combined = {**self.clarifications, **current}
        return tuple((question, answer) for question, answer in combined.items() if answer.strip())

    @computed_field
    @property
    def author_context(self) -> AuthorContext:
        questions = self.analysis.missing_information if self.analysis else []
        return author_context(self.idea, self.constraints, self.creator_answers(), questions, self.answers)

    def content_key(self) -> str:
        return json.dumps(
            {
                "idea": self.idea,
                # Auto was implicit in older saved projects and frozen demo recordings.
                **({"response_language": self.response_language}
                   if self.response_language != "auto" else {}),
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
