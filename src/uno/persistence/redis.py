"""Redis repository implementation."""

from __future__ import annotations

from typing import Any, Generic, Optional, Type, TypeVar, cast
from uuid import UUID

from redis.asyncio import Redis, RedisCluster

from uno.domain.aggregate import AggregateRoot
from uno.domain.events import DomainEvent
from uno.domain.repository import BaseRepository, RepositoryProtocol
from uno.uow.errors import ConcurrencyError, SerializationError
from uno.logging import LoggerProtocol, get_logger
from uno.serialization.redis_serializer import RedisSerializer, get_redis_serializer

E = TypeVar("E", bound=DomainEvent)
A = TypeVar("A", bound=AggregateRoot[Any])


def get_redis_repository(
    aggregate_type: Type[A],
    redis: Redis[bytes] | RedisCluster[bytes],
    key_prefix: str = "uno:aggregate:",
    compression: str = "none",
    logger: Optional[LoggerProtocol] = None,
) -> "RedisRepository[A]":
    """Create a Redis repository with the specified configuration.

    Args:
        aggregate_type: The aggregate class this repository manages
        redis: Redis client instance
        key_prefix: Prefix for Redis keys
        compression: Compression type ('gzip', 'lzma', 'zlib', 'none')
        logger: Logger instance (optional)

    Returns:
        Configured RedisRepository instance
    """
    return RedisRepository[A](
        aggregate_type=aggregate_type,
        redis=redis,
        key_prefix=key_prefix,
        compression=compression,
        logger=logger,
    )


class RedisRepository(BaseRepository[A, UUID], Generic[A]):
    """Redis implementation of the repository pattern.

    This repository uses Redis as the underlying storage and supports:
    - Compression of stored data
    - Versioning of aggregates
    - Optimistic concurrency control
    - Custom key prefixes
    - Configurable compression
    """

    def __init__(
        self,
        aggregate_type: Type[A],
        redis: Redis[bytes] | RedisCluster[bytes],
        key_prefix: str = "uno:aggregate:",
        compression: str = "none",
        logger: Optional[LoggerProtocol] = None,
    ) -> None:
        """Initialize the Redis repository.

        Args:
            aggregate_type: The aggregate class this repository manages
            redis: Redis client instance
            key_prefix: Prefix for Redis keys (default: "uno:aggregate:")
            compression: Compression type ('gzip', 'lzma', 'zlib', 'none')
            logger: Logger instance (optional)
        """
        super().__init__(logger=logger)
        self._aggregate_type = aggregate_type
        self._redis = redis
        self._key_prefix = f"{key_prefix}{aggregate_type.__name__.lower()}:"

        # Initialize serializer
        self._serializer = get_redis_serializer(
            key_prefix=self._key_prefix,
            compression=compression,
        )

    def _get_key(self, id: UUID) -> str:
        """Get the Redis key for an aggregate ID.
        
        Args:
            id: The ID of the aggregate
            
        Returns:
            The Redis key for the aggregate
        """
        return f"{self._key_prefix}{str(id)}"

    async def get(self, id: UUID) -> A | None:
        """Get an aggregate by ID.
        
        Args:
            id: The ID of the aggregate to retrieve
            
        Returns:
            The aggregate if found, None otherwise
            
        Raises:
            SerializationError: If there's an error deserializing the aggregate
            RuntimeError: If there's an error accessing Redis
        """
        key = self._get_key(id)
        try:
            data = await self._redis.get(key)
            if data is None:
                return None

            # Deserialize the aggregate
            return self._serializer.deserialize_value(data, self._aggregate_type)

        except SerializationError as e:
            self._logger.error(
                "Error deserializing aggregate %s: %s", id, e, exc_info=True
            )
            raise
        except Exception as e:
            self._logger.error("Error getting aggregate %s: %s", id, e, exc_info=True)
            raise RuntimeError(f"Failed to get aggregate {id}") from e

    async def add(self, entity: A) -> None:
        """Add a new aggregate.
        
        Args:
            entity: The aggregate to add
            
        Raises:
            ConcurrencyError: If an aggregate with the same ID already exists
            SerializationError: If there's an error serializing the aggregate
            RuntimeError: If there's an error accessing Redis
        """
        key = self._get_key(entity.id)
        try:
            # Check if aggregate already exists
            if await self._redis.exists(key):
                raise ConcurrencyError(f"Aggregate {entity.id} already exists")

            # Serialize and store the aggregate
            data = self._serializer.serialize_value(entity)
            await self._redis.set(key, data)

        except SerializationError as e:
            self._logger.error(
                "Error serializing aggregate %s: %s", entity.id, e, exc_info=True
            )
            raise
        except Exception as e:
            self._logger.error(
                "Error adding aggregate %s: %s", entity.id, e, exc_info=True
            )
            raise RuntimeError(f"Failed to add aggregate {entity.id}") from e

    async def update(self, entity: A) -> None:
        """Update an existing aggregate.
        
        Args:
            entity: The aggregate to update
            
        Raises:
            ConcurrencyError: If the aggregate doesn't exist
            SerializationError: If there's an error serializing the aggregate
            RuntimeError: If there's an error accessing Redis
        """
        key = self._get_key(entity.id)
        try:
            # Check if aggregate exists
            if not await self._redis.exists(key):
                raise ConcurrencyError(f"Aggregate {entity.id} does not exist")

            # Serialize and update the aggregate
            data = self._serializer.serialize_value(entity)
            await self._redis.set(key, data)

        except SerializationError as e:
            self._logger.error(
                "Error serializing aggregate %s: %s", entity.id, e, exc_info=True
            )
            raise
        except Exception as e:
            self._logger.error(
                "Error updating aggregate %s: %s", entity.id, e, exc_info=True
            )
            raise RuntimeError(f"Failed to update aggregate {entity.id}") from e

    async def remove(self, entity: A) -> None:
        """Remove an aggregate from the repository.
        
        Args:
            entity: The aggregate to remove
            
        Raises:
            RuntimeError: If there's an error accessing Redis
        """
        key = self._get_key(entity.id)
        try:
            deleted = await self._redis.delete(key)
            if deleted == 0:
                self._logger.warning(
                    "Attempted to delete non-existent aggregate %s", entity.id
                )
        except Exception as e:
            self._logger.error(
                "Error deleting aggregate %s: %s", entity.id, e, exc_info=True
            )
            raise RuntimeError(f"Failed to delete aggregate {entity.id}") from e
