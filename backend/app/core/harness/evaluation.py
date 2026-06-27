from abc import ABC, abstractmethod

from app.core.artifacts import EvaluationArtifact, PlanningArtifact
from app.core.domains import DomainPlugin


class EvaluationLayer(ABC):
    """Contract for evaluating a structured plan against domain criteria."""

    @abstractmethod
    def evaluate(self, planning: PlanningArtifact, domain: DomainPlugin) -> EvaluationArtifact:
        raise NotImplementedError
