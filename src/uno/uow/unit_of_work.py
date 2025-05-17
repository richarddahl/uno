"""Enhanced Unit of Work implementation with transaction management."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from abc import ABC, abstractmethod
from contextvars import ContextVar
from types import TracebackType
from typing import (
    Any,
    AsyncIterator,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)
from uuid import UUID

from pydantic import BaseModel, Field

from uno.domain.aggregate import AggregateRoot
from uno.domain.events import DomainEvent
from uno.injection import ContainerProtocol
from uno.logging import get_logger, LoggerProtocol

E = TypeVar("E", bound=DomainEvent)
A = TypeVar("A", bound=AggregateRoot[Any])
T = TypeVar("T")

# Context variable to track the current UoW instance
_current_uow: ContextVar[Optional[UnitOfWork]] = ContextVar(
    "_current_uow", default=None
)


class Savepoint(BaseModel):
    """Represents a savepoint within a transaction."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    version: int
    aggregate_versions: Dict[UUID, int] = Field(default_factory=dict)


class UnitOfWork(Generic[A, E], ABC):
    """Enhanced Unit of Work implementation with transaction management.

    This implementation supports:
    - Nested transactions using savepoints
    - Optimistic concurrency control
    - Automatic event collection and publishing
    - Context manager support

    Args:
        container: The dependency injection container
        isolation_level: The isolation level for transactions
        logger: Logger instance (optional)
    """

    def __init__(
        self,
        container: ContainerProtocol,
        isolation_level: str = "read_committed",
        logger: LoggerProtocol | None = None,
    ) -> None:
        self._container = container
        self._isolation_level = isolation_level
        self._logger = logger or get_logger("uno.uow")

        # Transaction state
        self._in_transaction = False
        self._transaction_depth = 0
        self._savepoints: List[Savepoint] = []
        self._aggregate_versions: Dict[UUID, int] = {}
        self._tracked_aggregates: Dict[UUID, A] = {}
        self._collected_events: List[E] = []
        self._parent: UnitOfWork | None = None

        # Set up repositories
        self._repositories: Dict[Type[A], Repository[A]] = {}

    @property
    def in_transaction(self) -> bool:
        """Check if the UoW is currently in a transaction."""
        return self._in_transaction

    @property
    def transaction_depth(self) -> int:
        """Get the current transaction nesting depth."""
        return self._transaction_depth

    async def __aenter__(self) -> UnitOfWork[A, E]:
        """Enter the async context manager."""
        await self.begin()
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the async context manager, committing or rolling back the transaction."""
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()

    async def begin(self) -> None:
        """Begin a new transaction."""
        if not self._in_transaction:
            self._in_transaction = True
            self._transaction_depth = 1
            self._current_uow_token = _current_uow.set(self)
            await self._begin()
        else:
            # Nested transaction - create a savepoint
            self._transaction_depth += 1
            savepoint = Savepoint(version=self._get_current_version())
            self._savepoints.append(savepoint)
            await self._create_savepoint(savepoint.id)

    async def commit(self) -> None:
        """Commit the current transaction."""
        if not self._in_transaction:
            raise RuntimeError("Not in a transaction")

        if self._transaction_depth > 1:
            # Nested transaction - release the savepoint
            self._transaction_depth -= 1
            savepoint = self._savepoints.pop()
            await self._release_savepoint(savepoint.id)
        else:
            # Root transaction - commit all changes
            try:
                await self._before_commit()
                await self._commit()
                await self._after_commit()
            finally:
                self._cleanup()

    async def rollback(self) -> None:
        """Roll back the current transaction."""
        if not self._in_transaction:
            raise RuntimeError("Not in a transaction")

        try:
            if self._transaction_depth > 1:
                # Nested transaction - roll back to savepoint
                savepoint = self._savepoints.pop()
                await self._rollback_to_savepoint(savepoint.id)
                self._restore_savepoint(savepoint)
            else:
                # Root transaction - roll back everything
                await self._rollback()
        finally:
            self._cleanup()

    def get_repository(self, aggregate_type: Type[A]) -> Repository[A]:
        """Get a repository for the given aggregate type."""
        if aggregate_type not in self._repositories:
            self._repositories[aggregate_type] = self._create_repository(aggregate_type)
        return self._repositories[aggregate_type]

    def collect_new_events(self) -> List[E]:
        """Collect all new domain events from tracked aggregates."""
        events: List[E] = []
        for aggregate in self._tracked_aggregates.values():
            events.extend(aggregate.pending_events)
            aggregate.clear_events()
        return events

    def track_aggregate(self, aggregate: A) -> None:
        """Track an aggregate in the current unit of work."""
        if not self._in_transaction:
            raise RuntimeError("Not in a transaction")

        self._tracked_aggregates[aggregate.id] = aggregate
        self._aggregate_versions[aggregate.id] = aggregate.version

    @contextlib.asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        """Context manager for a nested transaction."""
        await self.begin()
        try:
            yield
        except Exception:
            await self.rollback()
            raise
        else:
            await self.commit()

    def _get_current_version(self) -> int:
        """Get the current version number for optimistic concurrency."""
        return max(self._aggregate_versions.values(), default=0)

    def _restore_savepoint(self, savepoint: Savepoint) -> None:
        """Restore the state from a savepoint."""
        self._aggregate_versions = savepoint.aggregate_versions.copy()

    def _cleanup(self) -> None:
        """Clean up transaction state."""
        self._in_transaction = False
        self._transaction_depth = 0
        self._savepoints.clear()
        self._aggregate_versions.clear()
        self._tracked_aggregates.clear()
        self._collected_events.clear()

        # Reset context var if we're the current UoW
        if _current_uow.get() is self:
            _current_uow.set(None)

    @abstractmethod
    async def _begin(self) -> None:
        """Begin a new transaction."""
        ...

    @abstractmethod
    async def _commit(self) -> None:
        """Commit the current transaction."""
        ...

    @abstractmethod
    async def _rollback(self) -> None:
        """Roll back the current transaction."""
        ...

    @abstractmethod
    async def _create_savepoint(self, name: str) -> None:
        """Create a savepoint with the given name."""
        ...

    @abstractmethod
    async def _release_savepoint(self, name: str) -> None:
        """Release a savepoint."""
        ...

    @abstractmethod
    async def _rollback_to_savepoint(self, name: str) -> None:
        """Roll back to a savepoint."""
        ...

    @abstractmethod
    def _create_repository(self, aggregate_type: Type[A]) -> Repository[A]:
        """Create a repository for the given aggregate type."""
        ...

    async def _before_commit(self) -> None:
        """Called before committing the transaction."""
        # Verify optimistic concurrency
        for aggregate in self._tracked_aggregates.values():
            if aggregate.version != self._aggregate_versions[aggregate.id]:
                raise OptimisticConcurrencyError(
                    f"Concurrent modification detected for aggregate {aggregate.id}"
                )

    async def _after_commit(self) -> None:
        """Called after successfully committing the transaction."""
        # Collect and publish events
        self._collected_events = self.collect_new_events()
        # TODO: Publish events to event bus


def get_current_uow() -> UnitOfWork[Any, Any]:
    """Get the current unit of work from the context."""
    uow = _current_uow.get()
    if uow is None:
        raise RuntimeError("No active unit of work in context")
    return uow
