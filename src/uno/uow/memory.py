"""In-memory implementation of the Unit of Work pattern."""

from __future__ import annotations

import copy
from typing import Any, Type, TypeVar, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel

from uno.domain.aggregate import AggregateRoot
from uno.domain.events import DomainEvent
from uno.domain.repository import Repository, RepositoryFactory
from uno.injection import ContainerProtocol
from uno.logging import get_logger, LoggerProtocol
from uno.uow.base import BaseUnitOfWork
from uno.uow.errors import ConcurrencyError

E = TypeVar("E", bound=DomainEvent)
A = TypeVar("A", bound=AggregateRoot[Any])


class InMemoryUnitOfWork(BaseUnitOfWork[A]):
    """In-memory implementation of the Unit of Work pattern.
    
    This implementation is primarily intended for testing and development purposes.
    It maintains all state in memory and does not persist data between restarts.
    """

    def __init__(
        self,
        repository_factory: RepositoryFactory,
        logger: LoggerProtocol | None = None,
    ) -> None:
        """Initialize the in-memory Unit of Work.
        
        Args:
            repository_factory: Factory function to create repositories
            logger: Optional logger instance
        """
        super().__init__(repository_factory)
        self._logger = logger or get_logger("uno.uow.memory")
        self._data: Dict[Type[A], Dict[UUID, A]] = {}
        self._savepoints: List[Dict[Type[A], Dict[UUID, A]]] = []
        self._events: List[E] = []

    async def _begin(self) -> None:
        """Begin a new transaction."""
        self._savepoints.append(copy.deepcopy(self._data))

    async def _commit(self) -> None:
        """Commit the current transaction."""
        try:
            # Commit is a no-op in memory, just clear the savepoints
            self._savepoints.clear()
        except Exception as e:
            self._logger.error("Error committing transaction", exc_info=True)
            raise ConcurrencyError("Failed to commit transaction") from e

    async def _rollback(self) -> None:
        """Roll back the current transaction."""
        if self._savepoints:
            self._data = self._savepoints.pop()

    async def _create_savepoint(self, name: str) -> None:
        """Create a savepoint in the current transaction.
        
        Args:
            name: Name of the savepoint
        """
        self._savepoints.append(copy.deepcopy(self._data))

    async def _rollback_to_savepoint(self, name: str) -> None:
        """Roll back to a previously created savepoint.
        
        Args:
            name: Name of the savepoint to roll back to
        """
        if self._savepoints:
            self._data = self._savepoints[-1]

    async def _release_savepoint(self, name: str) -> None:
        """Release a savepoint.
        
        Args:
            name: Name of the savepoint to release
        """
        if self._savepoints:
            self._savepoints.pop()

    async def collect_new_events(self) -> List[E]:
        """Collect all new domain events from tracked aggregates."""
        events: List[E] = []
        for repo in self._repositories.values():
            for aggregate in repo.seen():
                while aggregate.pending_events:
                    event = aggregate.pending_events.pop(0)
                    events.append(cast(E, event))
        return events

    @classmethod
    def create(
        cls,
        container: ContainerProtocol,
        repository_factory: RepositoryFactory | None = None,
        **kwargs: Any,
    ) -> InMemoryUnitOfWork[A]:
        """Create a new in-memory Unit of Work instance.
        
        Args:
            container: The dependency injection container
            repository_factory: Optional repository factory
            **kwargs: Additional keyword arguments
            
        Returns:
            A new InMemoryUnitOfWork instance
        """
        if repository_factory is None:
            from uno.domain.repository import create_repository_factory
            repository_factory = create_repository_factory(container)
            
        return cls(repository_factory=repository_factory, **kwargs)
