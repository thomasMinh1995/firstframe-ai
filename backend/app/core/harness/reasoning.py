from abc import ABC, abstractmethod

from app.core.artifacts import IdeaArtifact, ReasoningArtifact
from app.core.domains import DomainPlugin


class ReasoningLayer(ABC):
    """Contract for interpreting and clarifying a raw creative idea.

    Implementations may use provider adapters in later sprints, but the runtime
    contract remains provider-independent.
    """

    @abstractmethod
    def reason(self, idea: IdeaArtifact, domain: DomainPlugin) -> ReasoningArtifact:
        raise NotImplementedError
