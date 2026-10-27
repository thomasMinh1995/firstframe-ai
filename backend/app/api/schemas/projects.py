import json
from collections.abc import Iterable
from typing import Annotated, Literal

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
from app.api.schemas.scenes import Scene, SceneId, SceneOutlineEdit, SceneText, StagingIdea, StagingSource, StagingUse
from app.application.language import ResponseLanguage
from app.application.clarification import MAX_CHOICES

from app.api.schemas.screenplays import ScreenplayEdit

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
    answers: list[ShortText] = Field(max_length=MAX_CHOICES)
    draft: StoryDraft | None
    screenplay: ScreenplayEdit | None = None
    scene_outline: SceneOutlineEdit | None = None
    scene_proposal_id: SceneId | None = None
    staging_use: StagingUse | None = None
    staging_idea_edits: dict[SceneId, SceneText] = Field(default_factory=dict, max_length=100)
    scene_proposal_previews: dict[SceneId, Annotated[list[Scene], Field(max_length=60)]] = Field(default_factory=dict, max_length=100)


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
        if feedback.revision_notes is not None:
            from app.application.revision_review import review_context

            context = review_context(self.draft.model_dump(), None, self.context.model_dump(), False)
            cards = {item["id"]: item["text"] for item in context["cards"]}
            decisions = {item["id"]: item for item in context["decisions"]}
            for note in feedback.revision_notes:
                decision = decisions.get(note.decision_id)
                if (note.artifact_id != self.artifact_id or decision is None
                        or note.decision_quote != decision["text"]
                        or note.decision_question != decision.get("question")
                        or len({target.target_id for target in note.targets}) != len(note.targets)
                        or any(cards.get(target.target_id) != target.quote for target in note.targets)):
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


class PlanGeneration(BaseModel):
    id: str
    created_at: str
    source_revision: int = Field(ge=0)
    source_content: str
    context: AuthorContext
    draft: StoryDraft
    critic_status: Literal["pending", "failed", "reviewed"] = "pending"
    applied_revision: int | None = Field(default=None, ge=0)
    feedback: EvaluationResponse | None = None
    feedback_source: FeedbackSource | None = None

    _parse_source = field_validator("feedback_source", mode="before")(parse_feedback_source)

    @model_validator(mode="after")
    def check_source(self) -> "PlanGeneration":
        source = self.feedback_source
        if source and (not source.matches(self.feedback) or source.draft != self.draft
                       or source.context != self.context):
            self.feedback_source = None
        return self


class ScenePlanSource(BaseModel):
    id: str
    project_revision: int
    version_id: str
    draft: StoryDraft
    context: AuthorContext
    response_language: ResponseLanguage


class SceneOutline(SceneOutlineEdit):
    source: ScenePlanSource


class Screenplay(ScreenplayEdit):
    source_revision: int
    source_outline: SceneOutline


class ScreenplayVersion(BaseModel):
    id: SceneId
    created_at: str
    screenplay: Screenplay


class SceneOutlineVersion(BaseModel):
    id: str
    created_at: str
    outline: SceneOutline


class SceneProposal(BaseModel):
    id: str
    created_at: str
    source_revision: int
    source_content: str
    source_outline: SceneOutline
    mode: Literal["list", "append", "develop", "staging"]
    target_scene_id: str | None = None
    instructions: str = ""
    status: Literal["pending", "ready", "failed", "applied", "discarded"] = "pending"
    scenes: list[Scene] = Field(default_factory=list)
    transitions: dict[str, str] = Field(default_factory=dict)
    staging_ideas: list[StagingIdea] = Field(default_factory=list)
    staging_sources: list[StagingSource] = Field(default_factory=list)
    staging_question: str = ""
    preview_scenes: list[Scene] | None = None
    provider: str | None = None
    model: str | None = None
    parameters: dict[str, object] = Field(default_factory=dict)
    prompt_version: str = "scene-suggestions-v1"
    error: str | None = None
    applied_revision: int | None = None


class SceneSketch(BaseModel):
    id: SceneId
    scene_id: SceneId
    created_at: str
    source_revision: int
    source_content: str
    source_outline: SceneOutline
    instructions: str = ""
    prompt: str
    prompt_version: str = "scene-sketch-v1"
    provider: str = "mflux"
    model: str = "filipstrand/Z-Image-Turbo-mflux-4bit"
    parameters: dict[str, object] = Field(default_factory=dict)
    status: Literal["pending", "ready", "failed", "discarded"] = "pending"
    asset_id: SceneId | None = None
    error: str | None = None
    diagnostic: str | None = None
    duration_seconds: float | None = None


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
    plan_generations: list[PlanGeneration] = Field(default_factory=list)
    scene_outline: SceneOutline | None = None
    screenplay: Screenplay | None = None
    screenplay_versions: list[ScreenplayVersion] = Field(default_factory=list)
    scene_versions: list[SceneOutlineVersion] = Field(default_factory=list)
    scene_proposals: list[SceneProposal] = Field(default_factory=list)
    staging_proposals: list[SceneProposal] = Field(default_factory=list)
    scene_sketches: list[SceneSketch] = Field(default_factory=list)
    selected_scene_sketches: dict[SceneId, SceneId] = Field(default_factory=dict)

    @computed_field
    @property
    def screenplay_source_is_current(self) -> bool:
        if not self.screenplay or not self.scene_outline:
            return False
        source, current = self.screenplay.source_outline, self.scene_outline
        # Version/revision metadata can change without changing source content.
        return (source.id == current.id and source.scenes == current.scenes
                and source.source == current.source and self.scene_source_is_current)

    @computed_field
    @property
    def applicable_sketch_ids(self) -> list[str]:
        return [s.id for s in self.scene_sketches if s.status == "ready"
                and s.source_outline == self.scene_outline and s.source_content == self.content_key()]

    @computed_field
    @property
    def applicable_scene_proposal_ids(self) -> list[str]:
        return [p.id for p in [*self.scene_proposals, *self.staging_proposals] if p.status == "ready"
                and p.source_outline == self.scene_outline and p.source_content == self.content_key()]

    @computed_field
    @property
    def scene_source_is_current(self) -> bool:
        source = self.scene_outline.source if self.scene_outline else None
        return bool(source and source.draft == self.draft
                    and source.context == self.author_context
                    and source.response_language == self.response_language)

    @computed_field
    @property
    def scene_handoff(self) -> dict[str, object] | None:
        outline = self.scene_outline
        if not outline or not outline.scenes or any(
            not scene.title.strip() or not scene.action.strip() for scene in outline.scenes
        ):
            return None
        return {"outline_id": outline.id, "version": outline.version,
                "project_revision": self.revision, "source_id": outline.source.id,
                "scenes": [scene.model_dump() for scene in outline.scenes]}

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
        for generation in self.plan_generations:
            source = generation.feedback_source
            if source and (source.project_id != self.id or source.revision > self.revision):
                generation.feedback_source = None
        return self

    @computed_field
    @property
    def applicable_plan_ids(self) -> list[str]:
        return [item.id for item in self.plan_generations
                if item.applied_revision is None and item.source_revision <= self.revision
                and item.source_content == self.content_key() and item.context == self.author_context]

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
