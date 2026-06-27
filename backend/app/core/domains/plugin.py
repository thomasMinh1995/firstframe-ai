from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class DomainMetadata:
    domain_id: str
    display_name: str
    version: str
    description: str
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DomainResource:
    resource_id: str
    title: str
    path: Path
    description: str = ""


@dataclass(frozen=True)
class DomainResourceCatalog:
    knowledge: tuple[DomainResource, ...] = field(default_factory=tuple)
    glossary: tuple[DomainResource, ...] = field(default_factory=tuple)
    prompts: tuple[DomainResource, ...] = field(default_factory=tuple)
    rubrics: tuple[DomainResource, ...] = field(default_factory=tuple)
    examples: tuple[DomainResource, ...] = field(default_factory=tuple)


class DomainPlugin(Protocol):
    """Provider-independent contract every creative domain plugin must satisfy."""

    @property
    def metadata(self) -> DomainMetadata:
        ...

    @property
    def knowledge(self) -> tuple[DomainResource, ...]:
        ...

    @property
    def glossary(self) -> tuple[DomainResource, ...]:
        ...

    @property
    def prompts(self) -> tuple[DomainResource, ...]:
        ...

    @property
    def rubrics(self) -> tuple[DomainResource, ...]:
        ...

    @property
    def examples(self) -> tuple[DomainResource, ...]:
        ...

    @property
    def resources(self) -> DomainResourceCatalog:
        ...
