"""
ConfigProtocol: Abstract base class for configuration providers.
Extend this protocol for any config service to be injected into core/infrastructure.
"""

from typing import Protocol, Any

class ConfigProtocol(Protocol):
    """Protocol for configuration providers."""
    def get(self, key: str, default: Any = None) -> Any:
        ...
