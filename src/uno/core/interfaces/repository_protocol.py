"""
RepositoryProtocol: Abstract base class for repository (port) interfaces.
Extend this protocol for any repository to be injected into core/infrastructure.
"""

from typing import Protocol, TypeVar, Generic

T = TypeVar("T")


class RepositoryProtocol(Protocol, Generic[T]):
    """Protocol for repository interfaces."""

    def add(self, entity: T) -> None: ...
    def get(self, entity_id: str) -> T | None: ...
    def remove(self, entity: T) -> None: ...
    def list(self) -> list[T]: ...
