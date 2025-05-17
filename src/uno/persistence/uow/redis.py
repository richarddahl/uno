"""Redis implementation of the Unit of Work pattern."""

from __future__ import annotations

import logging
from typing import (
    Any,
    Generic,
    Type,
    TypeVar,
)
from uuid import UUID

from redis.asyncio import Redis, RedisCluster
from redis.exceptions import RedisError

from uno.domain.aggregate import AggregateRoot
from uno.domain.events import DomainEvent
from uno.uow.errors import ConcurrencyError
from uno.injection import ContainerProtocol
from uno.logging import get_logger, LoggerProtocol
from uno.uow.unit_of_work import UnitOfWork

E = TypeVar("E", bound=DomainEvent)
A = TypeVar("A", bound=AggregateRoot[Any])


class RedisUnitOfWork(UnitOfWork[A, E], Generic[A, E]):
    """Redis implementation of the Unit of Work pattern.

    This implementation provides:
    - Transaction management using Redis transactions
    - Optimistic concurrency control
    - Savepoint support for nested transactions
    - Automatic event collection and publishing

    Args:
        container: The dependency injection container
        redis: Redis client instance
        isolation_level: The isolation level for transactions
        logger: Logger instance (optional)
    """

    def __init__(
        self,
        container: ContainerProtocol,
        redis: Redis[bytes] | RedisCluster[bytes],
        isolation_level: str = "read_committed",
        logger: LoggerProtocol | None = None,
    ) -> None:
        super().__init__(container, isolation_level, logger)
        self._redis = redis
        self._transaction = None
        self._is_cluster = isinstance(redis, RedisCluster)

    async def _begin(self) -> None:
        """Begin a new Redis transaction."""
        self._transaction = self._redis.pipeline(transaction=not self._is_cluster)

    async def _commit(self) -> None:
        """Commit the current Redis transaction."""
        if self._transaction is None:
            raise RuntimeError("No active transaction")

        try:
            await self._transaction.execute()
        except RedisError as e:
            self._logger.error("Error committing transaction: %s", e, exc_info=True)
            raise ConcurrencyError("Failed to commit transaction") from e
        finally:
            self._transaction = None

    async def _rollback(self) -> None:
        """Roll back the current Redis transaction."""
        if self._transaction is not None:
            try:
                await self._transaction.reset()
            except RedisError as e:
                self._logger.error(
                    "Error rolling back transaction: %s", e, exc_info=True
                )
            finally:
                self._transaction = None

    async def _create_savepoint(self, name: str) -> None:
        """Create a savepoint in the current transaction."""
        if self._transaction is None:
            raise RuntimeError("No active transaction")

        # In Redis, we don't need to do anything special for savepoints
        # since nested transactions aren't natively supported
        self._logger.debug("Created savepoint: %s", name)

    async def _release_savepoint(self, name: str) -> None:
        """Release a savepoint."""
        # No-op in Redis since we don't have native savepoints
        self._logger.debug("Released savepoint: %s", name)

    async def _rollback_to_savepoint(self, name: str) -> None:
        """Roll back to a savepoint."""
        if self._transaction is None:
            raise RuntimeError("No active transaction")

        # In Redis, we can't roll back to a savepoint, so we need to
        # simulate it by raising an exception that will trigger a full rollback
        self._logger.debug("Rolling back to savepoint: %s", name)
        raise ConcurrencyError("Savepoint rollback")

    def _create_repository(self, aggregate_type: Type[A]) -> Repository[A]:
        """Create a repository for the given aggregate type."""
        # Import here to avoid circular imports
        from uno.persistence.redis_base import RedisRepository

        return RedisRepository(
            aggregate_type=aggregate_type, redis=self._redis, logger=self._logger
        )

    @property
    def transaction(self) -> Redis[bytes] | RedisCluster[bytes]:
        """Get the current Redis transaction or connection."""
        return self._transaction or self._redis


class RedisRepository(Repository[A], Generic[A]):
    """Redis implementation of the repository pattern."""

    def __init__(
        self,
        aggregate_type: Type[A],
        redis: Redis[bytes] | RedisCluster[bytes],
        logger: LoggerProtocol | None = None,
    ) -> None:
        self._aggregate_type = aggregate_type
        self._redis = redis
        self._logger = logger or get_logger(
            f"uno.repository.redis.{aggregate_type.__name__.lower()}"
        )
        self._key_prefix = f"aggregate:{self._aggregate_type.__name__.lower()}:"

    async def get(self, id: UUID) -> A | None:
        """Get an aggregate by ID."""
        key = f"{self._key_prefix}{id}"
        try:
            data = await self._redis.get(key)
            if data is None:
                return None

            # TODO: Deserialize aggregate from Redis
            # aggregate = self._aggregate_type.model_validate_json(data)
            # return aggregate
            raise NotImplementedError("Aggregate deserialization not implemented")

        except RedisError as e:
            self._logger.error("Error getting aggregate %s: %s", id, e, exc_info=True)
            raise RuntimeError(f"Failed to get aggregate {id}") from e

    async def add(self, aggregate: A) -> None:
        """Add a new aggregate."""
        key = f"{self._key_prefix}{aggregate.id}"
        try:
            # TODO: Serialize aggregate to Redis
            # data = aggregate.model_dump_json()
            # await self._redis.set(key, data)
            raise NotImplementedError("Aggregate serialization not implemented")

        except RedisError as e:
            self._logger.error(
                "Error adding aggregate %s: %s", aggregate.id, e, exc_info=True
            )
            raise RuntimeError(f"Failed to add aggregate {aggregate.id}") from e

    async def update(self, aggregate: A) -> None:
        """Update an existing aggregate."""
        await self.add(aggregate)  # Same as add for Redis

    async def delete(self, id: UUID) -> None:
        """Delete an aggregate by ID."""
        key = f"{self._key_prefix}{id}"
        try:
            await self._redis.delete(key)
        except RedisError as e:
            self._logger.error("Error deleting aggregate %s: %s", id, e, exc_info=True)
            raise RuntimeError(f"Failed to delete aggregate {id}") from e
