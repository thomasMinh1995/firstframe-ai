from dataclasses import dataclass, field

import pytest

from app.core.domains import (
    DomainMetadata,
    DomainPluginNotFoundError,
    DomainRegistry,
    DomainResource,
    DomainResourceCatalog,
    DuplicateDomainPluginError,
)


@dataclass(frozen=True)
class StubDomainPlugin:
    metadata: DomainMetadata
    resources: DomainResourceCatalog = field(default_factory=DomainResourceCatalog)

    @property
    def knowledge(self) -> tuple[DomainResource, ...]:
        return self.resources.knowledge

    @property
    def glossary(self) -> tuple[DomainResource, ...]:
        return self.resources.glossary

    @property
    def prompts(self) -> tuple[DomainResource, ...]:
        return self.resources.prompts

    @property
    def rubrics(self) -> tuple[DomainResource, ...]:
        return self.resources.rubrics

    @property
    def examples(self) -> tuple[DomainResource, ...]:
        return self.resources.examples


def make_plugin(domain_id: str) -> StubDomainPlugin:
    return StubDomainPlugin(
        metadata=DomainMetadata(
            domain_id=domain_id,
            display_name="Test Domain",
            version="0.1.0",
            description="Test domain plugin.",
        )
    )


def test_registry_registers_and_retrieves_plugins() -> None:
    plugin = make_plugin("test-domain")
    registry = DomainRegistry()

    registry.register(plugin)

    assert registry.get("test-domain") is plugin
    assert registry.list() == (plugin,)
    assert registry.identifiers() == ("test-domain",)
    assert "test-domain" in registry


def test_registry_rejects_duplicate_domain_ids() -> None:
    registry = DomainRegistry([make_plugin("duplicate")])

    with pytest.raises(DuplicateDomainPluginError):
        registry.register(make_plugin("duplicate"))


def test_registry_rejects_empty_domain_ids() -> None:
    registry = DomainRegistry()

    with pytest.raises(ValueError):
        registry.register(make_plugin(" "))


def test_registry_reports_missing_plugins() -> None:
    registry = DomainRegistry()

    with pytest.raises(DomainPluginNotFoundError):
        registry.get("missing")
