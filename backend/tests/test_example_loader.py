from dataclasses import dataclass, field
from pathlib import Path

import pytest

from app.application.example_loader import (
    ExampleLibraryNotFoundError,
    ExampleLoader,
    InvalidExampleError,
)
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


def test_example_loader_loads_structured_examples(tmp_path: Path) -> None:
    domain = _domain("test-domain")
    examples_dir = tmp_path / "test-domain" / "examples"
    examples_dir.mkdir(parents=True)
    (examples_dir / "family.json").write_text(
        (
            '{"theme":"Family","genre":"Drama","user_idea":"A father says goodbye.",'
            '"story_plan":{"working_title":"Goodbye"},"evaluation_summary":{}}'
        ),
        encoding="utf-8",
    )
    loader = ExampleLoader(domains_root=tmp_path)

    examples = loader.load(domain)

    assert len(examples) == 1
    assert examples[0].source_id == "family"
    assert examples[0].theme == "Family"
    assert examples[0].genre == "Drama"
    assert examples[0].user_idea == "A father says goodbye."
    assert examples[0].payload["story_plan"] == {"working_title": "Goodbye"}


def test_example_loader_limits_returned_examples(tmp_path: Path) -> None:
    domain = _domain("test-domain")
    examples_dir = tmp_path / "test-domain" / "examples"
    examples_dir.mkdir(parents=True)
    (examples_dir / "a.json").write_text('{"theme":"A"}', encoding="utf-8")
    (examples_dir / "b.json").write_text('{"theme":"B"}', encoding="utf-8")
    loader = ExampleLoader(domains_root=tmp_path)

    examples = loader.load(domain, limit=1)

    assert len(examples) == 1
    assert examples[0].source_id == "a"


def test_example_loader_caches_loaded_examples(tmp_path: Path) -> None:
    domain = _domain("test-domain")
    example_path = tmp_path / "test-domain" / "examples" / "family.json"
    example_path.parent.mkdir(parents=True)
    example_path.write_text('{"theme":"Original"}', encoding="utf-8")
    loader = ExampleLoader(domains_root=tmp_path)

    assert loader.load(domain)[0].theme == "Original"

    example_path.write_text('{"theme":"Changed"}', encoding="utf-8")

    assert loader.load(domain)[0].theme == "Original"


def test_example_loader_raises_meaningful_error_for_missing_library(tmp_path: Path) -> None:
    domain = _domain("test-domain")
    loader = ExampleLoader(domains_root=tmp_path)

    with pytest.raises(ExampleLibraryNotFoundError, match="test-domain"):
        loader.load(domain)


def test_example_loader_raises_meaningful_error_for_invalid_json(tmp_path: Path) -> None:
    domain = _domain("test-domain")
    example_path = tmp_path / "test-domain" / "examples" / "broken.json"
    example_path.parent.mkdir(parents=True)
    example_path.write_text("{not-json", encoding="utf-8")
    loader = ExampleLoader(domains_root=tmp_path)

    with pytest.raises(InvalidExampleError, match="broken.json"):
        loader.load(domain)


def _domain(domain_id: str) -> StubDomainPlugin:
    return StubDomainPlugin(
        metadata=DomainMetadata(
            domain_id=domain_id,
            display_name="Test Domain",
            version="0.1.0",
            description="Test domain.",
        )
    )
