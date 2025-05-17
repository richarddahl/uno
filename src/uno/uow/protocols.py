"""Unit of Work protocol definitions."""

from types import TracebackType
from typing import Any, Protocol, TypeVar, Generic
from typing_extensions import Self

from uno.domain.repository import RepositoryProtocol

T = TypeVar("T")
ID = TypeVar("ID")


class RepositoryFactory(Protocol):
    """Protocol for repository factory that creates repositories on demand."""

    def __call__(self, aggregate_type: type[T]) -> RepositoryProtocol[T, Any]:
        """Create a repository for the given aggregate type."""
        ...


class UnitOfWorkProtocol(Protocol):
    """Protocol interface for managing transactions and repositories."""

    async def __aenter__(self) -> Self:
        """Enter the async context manager."""
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the async context manager, committing or rolling back the transaction."""
        ...

    async def commit(self) -> None:
        """Commit all changes made in this unit of work."""
        ...

    async def rollback(self) -> None:
        """Roll back all changes made in this unit of work."""
        ...

    def get_repository(self, aggregate_type: type[T]) -> RepositoryProtocol[T, Any]:
        """Get a repository for the given aggregate type."""
        ...

    def collect_new_events(self) -> list[Any]:
        """Collect all new domain events from tracked aggregates."""
        ...


class UnitOfWorkManagerProtocol(Protocol):
    """Protocol for managing the lifecycle of Unit of Work instances."""

    async def start(self) -> UnitOfWorkProtocol:
        """Start a new unit of work."""
        ...

    async def commit(self, uow: UnitOfWorkProtocol) -> None:
        """Commit a unit of work."""
        ...

    async def rollback(self, uow: UnitOfWorkProtocol) -> None:
        """Roll back a unit of work."""
        ...
