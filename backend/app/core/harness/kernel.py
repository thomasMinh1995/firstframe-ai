from typing import Protocol

from app.core.artifacts import EvaluationArtifact, IdeaArtifact, PlanningArtifact, ReasoningArtifact
from app.core.domains import DomainRegistry


class CreativeReasoningKernel(Protocol):
    """Runtime boundary for orchestrating Harness layers.

    Sprint 2 defines the contract only. A later implementation should compose a
    domain registry with concrete Reasoning, Planning, and Evaluation layers.
    """

    @property
    def domains(self) -> DomainRegistry:
        ...

    def reason(self, idea: IdeaArtifact) -> ReasoningArtifact:
        ...

    def plan(self, reasoning: ReasoningArtifact) -> PlanningArtifact:
        ...

    def evaluate(self, planning: PlanningArtifact) -> EvaluationArtifact:
        ...
