from dataclasses import dataclass, field
from pathlib import Path

import pytest

from app.application.knowledge_loader import (
    InvalidKnowledgeError,
    KnowledgeLoader,
    KnowledgeNotFoundError,
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


def test_knowledge_loader_loads_json_by_logical_name(tmp_path: Path) -> None:
    domain = _domain("test-domain")
    knowledge_dir = tmp_path / "test-domain" / "knowledge"
    knowledge_dir.mkdir(parents=True)
    (knowledge_dir / "film_rules.json").write_text(
        '{"rules":[{"rule":"Keep one central conflict."}]}',
        encoding="utf-8",
    )

    loader = KnowledgeLoader(domains_root=tmp_path)

    assert loader.load("film_rules", domain) == {
        "rules": [{"rule": "Keep one central conflict."}]
    }


def test_knowledge_loader_raises_meaningful_error_for_missing_file(tmp_path: Path) -> None:
    domain = _domain("test-domain")
    loader = KnowledgeLoader(domains_root=tmp_path)

    with pytest.raises(KnowledgeNotFoundError, match="film_rules"):
        loader.load("film_rules", domain)


def test_knowledge_loader_raises_meaningful_error_for_invalid_json(tmp_path: Path) -> None:
    domain = _domain("test-domain")
    knowledge_path = tmp_path / "test-domain" / "knowledge" / "film_rules.json"
    knowledge_path.parent.mkdir(parents=True)
    knowledge_path.write_text("{not-json", encoding="utf-8")
    loader = KnowledgeLoader(domains_root=tmp_path)

    with pytest.raises(InvalidKnowledgeError, match="film_rules"):
        loader.load("film_rules", domain)


def test_knowledge_loader_caches_loaded_json(tmp_path: Path) -> None:
    domain = _domain("test-domain")
    knowledge_path = tmp_path / "test-domain" / "knowledge" / "film_rules.json"
    knowledge_path.parent.mkdir(parents=True)
    knowledge_path.write_text('{"rules":["original"]}', encoding="utf-8")
    loader = KnowledgeLoader(domains_root=tmp_path)

    assert loader.load("film_rules", domain) == {"rules": ["original"]}

    knowledge_path.write_text('{"rules":["changed"]}', encoding="utf-8")

    assert loader.load("film_rules", domain) == {"rules": ["original"]}


def test_knowledge_loader_loads_rubric_by_logical_name(tmp_path: Path) -> None:
    domain = _domain("test-domain")
    rubric_path = tmp_path / "test-domain" / "rubrics" / "story_rubric.json"
    rubric_path.parent.mkdir(parents=True)
    rubric_path.write_text(
        '{"rubric":{"criteria":[{"name":"Story Clarity"}]}}',
        encoding="utf-8",
    )
    loader = KnowledgeLoader(domains_root=tmp_path)

    assert loader.load_rubric("story_rubric", domain) == {
        "rubric": {"criteria": [{"name": "Story Clarity"}]}
    }


def test_knowledge_loader_caches_loaded_rubric(tmp_path: Path) -> None:
    domain = _domain("test-domain")
    rubric_path = tmp_path / "test-domain" / "rubrics" / "story_rubric.json"
    rubric_path.parent.mkdir(parents=True)
    rubric_path.write_text('{"rubric":{"name":"original"}}', encoding="utf-8")
    loader = KnowledgeLoader(domains_root=tmp_path)

    assert loader.load_rubric("story_rubric", domain) == {"rubric": {"name": "original"}}

    rubric_path.write_text('{"rubric":{"name":"changed"}}', encoding="utf-8")

    assert loader.load_rubric("story_rubric", domain) == {"rubric": {"name": "original"}}


def _domain(domain_id: str) -> StubDomainPlugin:
    return StubDomainPlugin(
        metadata=DomainMetadata(
            domain_id=domain_id,
            display_name="Test Domain",
            version="0.1.0",
            description="Test domain.",
        )
    )
