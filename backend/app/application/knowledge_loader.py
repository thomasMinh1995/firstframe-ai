import json
from pathlib import Path
from typing import Any

from app.core.domains import DomainPlugin


class KnowledgeNotFoundError(FileNotFoundError):
    """Raised when a domain knowledge file cannot be found."""


class InvalidKnowledgeError(ValueError):
    """Raised when a domain knowledge file is not valid JSON."""


class KnowledgeLoader:
    """Loads and caches JSON knowledge files for the active creative domain."""

    def __init__(self, domains_root: Path | None = None) -> None:
        self._domains_root = domains_root or Path(__file__).resolve().parents[3] / "domains"
        self._cache: dict[tuple[str, str, str], Any] = {}

    def load(self, logical_name: str, domain: DomainPlugin) -> Any:
        return self._load_json(logical_name, domain, folder="knowledge")

    def load_rubric(self, logical_name: str, domain: DomainPlugin) -> Any:
        return self._load_json(logical_name, domain, folder="rubrics")

    def _load_json(self, logical_name: str, domain: DomainPlugin, folder: str) -> Any:
        domain_id = domain.metadata.domain_id
        cache_key = (domain_id, folder, logical_name)
        if cache_key in self._cache:
            return self._cache[cache_key]

        resource_path = self._resource_path(logical_name, domain, folder)
        if not resource_path.exists():
            raise KnowledgeNotFoundError(
                f"Knowledge resource '{logical_name}' not found for domain '{domain_id}' at "
                f"{resource_path}."
            )

        try:
            resource = json.loads(resource_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise InvalidKnowledgeError(
                f"Knowledge resource '{logical_name}' for domain '{domain_id}' is not valid JSON."
            ) from error

        self._cache[cache_key] = resource
        return resource

    def _resource_path(self, logical_name: str, domain: DomainPlugin, folder: str) -> Path:
        return (
            self._domains_root
            / domain.metadata.domain_id
            / folder
            / f"{logical_name}.json"
        )
