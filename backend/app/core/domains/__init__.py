"""Domain plugin contracts."""

from app.core.domains.plugin import (
    DomainMetadata,
    DomainPlugin,
    DomainResource,
    DomainResourceCatalog,
)
from app.core.domains.registry import (
    DomainPluginNotFoundError,
    DomainRegistry,
    DuplicateDomainPluginError,
)

__all__ = [
    "DomainMetadata",
    "DomainPlugin",
    "DomainPluginNotFoundError",
    "DomainRegistry",
    "DomainResource",
    "DomainResourceCatalog",
    "DuplicateDomainPluginError",
]
