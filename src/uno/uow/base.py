"""Base Unit of Work implementation."""

from typing import Any, TypeVar, Type, Optional, Dict, List
from contextlib import asynccontextmanager
from collections import defaultdict

from pydantic import BaseModel
from typing_extensions import Self

from uno.domain.events import DomainEvent
from uno.domain.aggregate import AggregateRoot
from uno.domain.repository import Repository
from uno.uow.protocols import RepositoryFactory
from uno.uow.base import UnitOfWork
from uno.uow.errors import RepositoryError

T = TypeVar("T", bound=AggregateRoot)


class BaseUnitOfWork(UnitOfWork):
    """Base implementation of the Unit of Work pattern.

    This class provides a foundation for implementing concrete UoW classes
    with different storage backends.
    """

    def __init__(self, repository_factory: RepositoryFactory) -> None:
        """Initialize the Unit of Work.

        Args:
            repository_factory: Factory function to create repositories
        """
        self._repository_factory = repository_factory
        self._repositories: Dict[Type[AggregateRoot], Repository] = {}
        self._events: List[DomainEvent] = []
        self._committed = False
        self._disposed = False

    async def __aenter__(self) -> Self:
        """Enter the async context manager."""
        if self._disposed:
            raise RuntimeError("Cannot reuse a disposed Unit of Work")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the async context manager, committing or rolling back the transaction."""
        try:
            if exc_type is None:
                await self.commit()
            else:
                await self.rollback()
        finally:
            await self.dispose()

    def get_repository(self, aggregate_type: Type[T]) -> Repository[T]:
        """Get a repository for the given aggregate type."""
        if aggregate_type not in self._repositories:
            self._repositories[aggregate_type] = self._repository_factory(
                aggregate_type
            )
        return self._repositories[aggregate_type]

    def collect_new_events(self) -> List[DomainEvent]:
        """Collect all new domain events from tracked aggregates."""
        events = []
        for repo in self._repositories.values():
            for aggregate in repo.seen():
                while aggregate.pending_events:
                    events.append(aggregate.pending_events.pop(0))
        return events

    async def commit(self) -> None:
        """Commit all changes made in this unit of work."""
        if self._committed:
            raise RuntimeError("This Unit of Work was already committed")

        if self._disposed:
            raise RuntimeError("Cannot commit a disposed Unit of Work")

        try:
            # Collect all events before committing
            self._events = self.collect_new_events()

            # Persist all changes
            for repo in self._repositories.values():
                await repo.persist_all()

            # Commit the transaction
            await self._commit()
            self._committed = True

        except Exception as exc:
            await self.rollback()
            raise RepositoryError("Failed to commit Unit of Work") from exc

    async def rollback(self) -> None:
        """Roll back all changes made in this unit of work."""
        if self._disposed:
            return

        try:
            await self._rollback()

            # Clear any pending changes in repositories
            for repo in self._repositories.values():
                repo.clear()

            self._events.clear()

        except Exception as exc:
            raise RepositoryError("Failed to roll back Unit of Work") from exc

    async def dispose(self) -> None:
        """Clean up resources used by this Unit of Work."""
        if self._disposed:
            return

        try:
            # Clear repositories
            for repo in self._repositories.values():
                if hasattr(repo, "dispose"):
                    await repo.dispose()

            self._repositories.clear()
            self._events.clear()

        finally:
            self._disposed = True

    async def _commit(self) -> None:
        """Commit the underlying transaction."""
        raise NotImplementedError

    async def _rollback(self) -> None:
        """Roll back the underlying transaction."""
        raise NotImplementedError
