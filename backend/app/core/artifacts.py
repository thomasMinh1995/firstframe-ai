from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


ArtifactKind = Literal["idea", "reasoning", "planning", "evaluation", "story_plan"]


@dataclass(frozen=True)
class ArtifactMetadata:
    artifact_id: str
    domain_id: str
    kind: ArtifactKind
    created_at: datetime | None = None
    version: str = "1"


@dataclass(frozen=True)
class Constraint:
    name: str
    value: str


@dataclass(frozen=True)
class IdeaArtifact:
    metadata: ArtifactMetadata
    text: str
    constraints: tuple[Constraint, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ReasoningNote:
    label: str
    content: str


@dataclass(frozen=True)
class ReasoningArtifact:
    metadata: ArtifactMetadata
    source_idea_id: str
    notes: tuple[ReasoningNote, ...] = field(default_factory=tuple)
    open_questions: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PlanSection:
    section_id: str
    title: str
    purpose: str
    content: str


@dataclass(frozen=True)
class PlanningArtifact:
    metadata: ArtifactMetadata
    source_reasoning_id: str
    sections: tuple[PlanSection, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class EvaluationFinding:
    criterion_id: str
    message: str
    severity: Literal["info", "warning", "error"]
    score: int | None = None


@dataclass(frozen=True)
class EvaluationArtifact:
    metadata: ArtifactMetadata
    source_planning_id: str
    findings: tuple[EvaluationFinding, ...] = field(default_factory=tuple)
    passed: bool | None = None


@dataclass(frozen=True)
class StoryPlanArtifact:
    metadata: ArtifactMetadata
    source_planning_id: str
    title: str | None = None
    logline: str | None = None
    sections: tuple[PlanSection, ...] = field(default_factory=tuple)
