"""PostgreSQL implementation of the Unit of Work pattern."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Type, TypeVar, Dict, List, Optional, cast
from uuid import UUID

import asyncpg
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


class PostgresUnitOfWork(BaseUnitOfWork[A]):
    """PostgreSQL implementation of the Unit of Work pattern.
    
    This implementation uses PostgreSQL's transaction and savepoint features
    to provide ACID guarantees for operations within a unit of work.
    """

    def __init__(
        self,
        pool: asyncpg.Pool,
        repository_factory: RepositoryFactory,
        logger: LoggerProtocol | None = None,
    ) -> None:
        """Initialize the PostgreSQL Unit of Work.
        
        Args:
            pool: AsyncPG connection pool
            repository_factory: Factory function to create repositories
            logger: Optional logger instance
        """
        super().__init__(repository_factory)
        self._pool = pool
        self._logger = logger or get_logger("uno.persistence.uow.postgres")
        self._connection: asyncpg.Connection | None = None
        self._transaction: asyncpg.transaction.Transaction | None = None
        self._savepoints: Dict[str, str] = {}

    async def _begin(self) -> None:
        """Begin a new transaction."""
        if self._connection is None:
            self._connection = await self._pool.acquire()
        self._transaction = self._connection.transaction()
        await self._transaction.start()

    async def _commit(self) -> None:
        """Commit the current transaction."""
        if self._transaction is not None:
            try:
                await self._transaction.commit()
            except asyncpg.PostgresError as e:
                self._logger.error("Error committing transaction", exc_info=True)
                raise ConcurrencyError("Failed to commit transaction") from e
            finally:
                self._cleanup()

    async def _rollback(self) -> None:
        """Roll back the current transaction."""
        if self._transaction is not None:
            try:
                await self._transaction.rollback()
            except asyncpg.PostgresError as e:
                self._logger.error("Error rolling back transaction", exc_info=True)
                raise ConcurrencyError("Failed to roll back transaction") from e
            finally:
                self._cleanup()

    async def _create_savepoint(self, name: str) -> None:
        """Create a savepoint in the current transaction.
        
        Args:
            name: Name of the savepoint
        """
        if self._connection is not None:
            savepoint_name = f"savepoint_{name}"
            await self._connection.execute(f"SAVEPOINT {savepoint_name}")
            self._savepoints[name] = savepoint_name

    async def _rollback_to_savepoint(self, name: str) -> None:
        """Roll back to a previously created savepoint.
        
        Args:
            name: Name of the savepoint to roll back to
        """
        if self._connection is not None and name in self._savepoints:
            savepoint_name = self._savepoints[name]
            await self._connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")

    async def _release_savepoint(self, name: str) -> None:
        """Release a savepoint.
        
        Args:
            name: Name of the savepoint to release
        """
        if self._connection is not None and name in self._savepoints:
            savepoint_name = self._savepoints.pop(name)
            await self._connection.execute(f"RELEASE SAVEPOINT {savepoint_name}")

    async def collect_new_events(self) -> List[E]:
        """Collect all new domain events from tracked aggregates."""
        events: List[E] = []
        for repo in self._repositories.values():
            for aggregate in repo.seen():
                while aggregate.pending_events:
                    event = aggregate.pending_events.pop(0)
                    events.append(cast(E, event))
        return events

    def _cleanup(self) -> None:
        """Clean up resources."""
        if self._connection is not None:
            # Return the connection to the pool
            asyncio.create_task(self._pool.release(self._connection))
            self._connection = None
        self._transaction = None
        self._savepoints.clear()

    @classmethod
    async def create(
        cls,
        container: ContainerProtocol,
        repository_factory: RepositoryFactory | None = None,
        **kwargs: Any,
    ) -> PostgresUnitOfWork[A]:
        """Create a new PostgreSQL Unit of Work instance.
        
        Args:
            container: The dependency injection container
            repository_factory: Optional repository factory
            **kwargs: Additional keyword arguments
            
        Returns:
            A new PostgresUnitOfWork instance
        """
        if repository_factory is None:
            from uno.domain.repository import create_repository_factory
            repository_factory = create_repository_factory(container)
            
        # Get the connection pool from the container
        pool = await container.resolve(asyncpg.Pool)
        return cls(pool=pool, repository_factory=repository_factory, **kwargs)
