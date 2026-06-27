from dataclasses import dataclass, field
from pathlib import Path

import pytest

from app.application.prompt_loader import PromptLoader, PromptNotFoundError
from app.core.domains import DomainMetadata, DomainResource, DomainResourceCatalog


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


def test_prompt_loader_loads_prompt_by_logical_name(tmp_path: Path) -> None:
    domain = _domain("test-domain")
    prompt_dir = tmp_path / "test-domain" / "prompts"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "story_planner_prompt.md").write_text("Prompt text", encoding="utf-8")

    loader = PromptLoader(domains_root=tmp_path)

    assert loader.load("story_planner", domain) == "Prompt text"


def test_prompt_loader_raises_meaningful_error_for_missing_prompt(tmp_path: Path) -> None:
    domain = _domain("test-domain")
    loader = PromptLoader(domains_root=tmp_path)

    with pytest.raises(PromptNotFoundError, match="story_planner"):
        loader.load("story_planner", domain)


def test_prompt_loader_caches_prompt_content(tmp_path: Path) -> None:
    domain = _domain("test-domain")
    prompt_path = tmp_path / "test-domain" / "prompts" / "story_planner_prompt.md"
    prompt_path.parent.mkdir(parents=True)
    prompt_path.write_text("Original prompt", encoding="utf-8")
    loader = PromptLoader(domains_root=tmp_path)

    assert loader.load("story_planner", domain) == "Original prompt"

    prompt_path.write_text("Changed prompt", encoding="utf-8")

    assert loader.load("story_planner", domain) == "Original prompt"


def _domain(domain_id: str) -> StubDomainPlugin:
    return StubDomainPlugin(
        metadata=DomainMetadata(
            domain_id=domain_id,
            display_name="Test Domain",
            version="0.1.0",
            description="Test domain.",
        )
    )
