"""
DatabaseProviderProtocol: Abstract base class for database provider implementations.
Extend this protocol for any DB engine/session provider to be injected via DI.
"""
from typing import Protocol, Any

class DatabaseProviderProtocol(Protocol):
    """Protocol for database provider implementations."""
    def get_engine(self) -> Any:
        ...
    def get_session(self) -> Any:
        ...
