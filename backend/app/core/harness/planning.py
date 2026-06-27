from abc import ABC, abstractmethod

from app.core.artifacts import PlanningArtifact, ReasoningArtifact
from app.core.domains import DomainPlugin


class PlanningLayer(ABC):
    """Contract for turning clarified creative intent into a structured plan."""

    @abstractmethod
    def plan(self, reasoning: ReasoningArtifact, domain: DomainPlugin) -> PlanningArtifact:
        raise NotImplementedError
