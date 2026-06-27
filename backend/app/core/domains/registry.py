from collections.abc import Iterable

from app.core.domains.plugin import DomainPlugin


class DuplicateDomainPluginError(ValueError):
    """Raised when a domain identifier is registered more than once."""


class DomainPluginNotFoundError(KeyError):
    """Raised when a requested domain identifier is not registered."""


class DomainRegistry:
    """Single entry point for registering and retrieving domain plugins."""

    def __init__(self, plugins: Iterable[DomainPlugin] = ()) -> None:
        self._plugins: dict[str, DomainPlugin] = {}
        for plugin in plugins:
            self.register(plugin)

    def register(self, plugin: DomainPlugin) -> None:
        domain_id = plugin.metadata.domain_id.strip()
        if not domain_id:
            raise ValueError("Domain plugin metadata.domain_id must not be empty.")
        if domain_id in self._plugins:
            raise DuplicateDomainPluginError(f"Domain plugin already registered: {domain_id}")
        self._plugins[domain_id] = plugin

    def list(self) -> tuple[DomainPlugin, ...]:
        return tuple(self._plugins.values())

    def get(self, domain_id: str) -> DomainPlugin:
        normalized_domain_id = domain_id.strip()
        try:
            return self._plugins[normalized_domain_id]
        except KeyError as error:
            raise DomainPluginNotFoundError(normalized_domain_id) from error

    def identifiers(self) -> tuple[str, ...]:
        return tuple(self._plugins.keys())

    def __contains__(self, domain_id: object) -> bool:
        if not isinstance(domain_id, str):
            return False
        return domain_id.strip() in self._plugins
