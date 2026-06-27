from pathlib import Path

from app.core.domains import DomainPlugin


class PromptNotFoundError(FileNotFoundError):
    """Raised when a domain prompt cannot be found."""


class PromptLoader:
    """Loads and caches prompt files for the active creative domain."""

    def __init__(self, domains_root: Path | None = None) -> None:
        self._domains_root = domains_root or Path(__file__).resolve().parents[3] / "domains"
        self._cache: dict[tuple[str, str], str] = {}

    def load(self, logical_name: str, domain: DomainPlugin) -> str:
        domain_id = domain.metadata.domain_id
        cache_key = (domain_id, logical_name)
        if cache_key in self._cache:
            return self._cache[cache_key]

        prompt_path = self._prompt_path(logical_name, domain)
        if not prompt_path.exists():
            raise PromptNotFoundError(
                f"Prompt '{logical_name}' not found for domain '{domain_id}' at {prompt_path}."
            )

        prompt = prompt_path.read_text(encoding="utf-8").strip()
        self._cache[cache_key] = prompt
        return prompt

    def _prompt_path(self, logical_name: str, domain: DomainPlugin) -> Path:
        return (
            self._domains_root
            / domain.metadata.domain_id
            / "prompts"
            / f"{logical_name}_prompt.md"
        )
