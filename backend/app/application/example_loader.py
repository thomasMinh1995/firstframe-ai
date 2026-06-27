import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.domains import DomainPlugin


class ExampleLibraryNotFoundError(FileNotFoundError):
    """Raised when a domain example library cannot be found."""


class InvalidExampleError(ValueError):
    """Raised when a domain example file is not valid JSON."""


@dataclass(frozen=True)
class DomainExample:
    """Reusable structured example from a domain example library."""

    source_id: str
    theme: str
    genre: str
    user_idea: str
    payload: dict[str, Any]


class ExampleLoader:
    """Loads and caches structured examples for the active creative domain."""

    def __init__(self, domains_root: Path | None = None) -> None:
        self._domains_root = domains_root or Path(__file__).resolve().parents[3] / "domains"
        self._cache: dict[str, tuple[DomainExample, ...]] = {}

    def load(self, domain: DomainPlugin, limit: int | None = None) -> tuple[DomainExample, ...]:
        domain_id = domain.metadata.domain_id
        if domain_id not in self._cache:
            self._cache[domain_id] = self._load_domain_examples(domain)

        examples = self._cache[domain_id]
        if limit is None:
            return examples
        return examples[:limit]

    def _load_domain_examples(self, domain: DomainPlugin) -> tuple[DomainExample, ...]:
        domain_id = domain.metadata.domain_id
        examples_dir = self._examples_dir(domain)
        if not examples_dir.exists():
            raise ExampleLibraryNotFoundError(
                f"Example library not found for domain '{domain_id}' at {examples_dir}."
            )

        examples: list[DomainExample] = []
        for example_path in sorted(examples_dir.glob("*.json")):
            try:
                payload = json.loads(example_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as error:
                raise InvalidExampleError(
                    f"Example '{example_path.name}' for domain '{domain_id}' is not valid JSON."
                ) from error

            if not isinstance(payload, dict):
                raise InvalidExampleError(
                    f"Example '{example_path.name}' for domain '{domain_id}' must be a JSON object."
                )

            examples.append(
                DomainExample(
                    source_id=example_path.stem,
                    theme=str(payload.get("theme", "")),
                    genre=str(payload.get("genre", "")),
                    user_idea=str(payload.get("user_idea", "")),
                    payload=payload,
                )
            )

        return tuple(examples)

    def _examples_dir(self, domain: DomainPlugin) -> Path:
        return self._domains_root / domain.metadata.domain_id / "examples"
