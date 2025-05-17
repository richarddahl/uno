"""Redis-based snapshot store for aggregate roots."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Generic, Optional, Type, TypeVar, cast
from uuid import UUID

from redis.asyncio import Redis, RedisCluster
from redis.exceptions import RedisError

from uno.domain.aggregate import AggregateRoot, AggregateSnapshot
from uno.domain.events import DomainEvent
from uno.event_store.errors import SnapshotStoreError
from uno.injection import ContainerProtocol
from uno.logging import get_logger, LoggerProtocol

E = TypeVar('E', bound=DomainEvent)
A = TypeVar('A', bound=AggregateRoot[Any])
S = TypeVar('S', bound=AggregateSnapshot)

class RedisSnapshotStore(Generic[A, E, S]):
    """Redis-based snapshot store for aggregate roots.
    
    This store provides efficient storage and retrieval of aggregate snapshots
    to optimize event replay performance.
    
    Args:
        container: The dependency injection container
        redis: Redis client instance (optional, will create one if not provided)
        prefix: Key prefix for all snapshot keys
        ttl_seconds: Optional TTL in seconds for snapshots
        logger: Logger instance (optional)
    """
    
    def __init__(
        self,
        container: ContainerProtocol,
        redis: Redis[bytes] | RedisCluster[bytes] | None = None,
        prefix: str = "snapshot:",
        ttl_seconds: int | None = None,
        logger: LoggerProtocol | None = None,
    ) -> None:
        self._container = container
        self._redis = redis
        self._prefix = prefix
        self._ttl_seconds = ttl_seconds
        self._logger = logger or get_logger("uno.event_store.redis_snapshot_store")
    
    async def get_snapshot(
        self,
        aggregate_type: Type[A],
        aggregate_id: UUID,
    ) -> tuple[S | None, int]:
        """Get the latest snapshot for an aggregate.
        
        Args:
            aggregate_type: The type of the aggregate
            aggregate_id: The ID of the aggregate
            
        Returns:
            A tuple of (snapshot, version) if found, (None, 0) otherwise
            
        Raises:
            SnapshotStoreError: If there's an error reading from Redis
        """
        if self._redis is None:
            raise SnapshotStoreError("Redis client not initialized")
            
        try:
            key = f"{self._prefix}{aggregate_type.__name__.lower()}:{aggregate_id}"
            data = await self._redis.get(key)
            
            if not data:
                return None, 0
                
            snapshot_data = json.loads(data)
            snapshot = aggregate_type.get_snapshot_type().model_validate(snapshot_data)
            return snapshot, snapshot.version
            
        except Exception as e:
            self._logger.error("Error getting snapshot: %s", e, exc_info=True)
            raise SnapshotStoreError(f"Failed to get snapshot: {e}") from e
    
    async def save_snapshot(
        self,
        aggregate: A,
        version: int | None = None,
    ) -> None:
        """Save a snapshot of an aggregate's state.
        
        Args:
            aggregate: The aggregate to snapshot
            version: The version of the aggregate to snapshot (defaults to current version)
            
        Raises:
            SnapshotStoreError: If there's an error saving the snapshot
        """
        if self._redis is None:
            raise SnapshotStoreError("Redis client not initialized")
            
        try:
            # Create the snapshot
            snapshot = aggregate.to_snapshot()
            snapshot.version = version if version is not None else aggregate.version
            
            # Prepare the data
            key = f"{self._prefix}{aggregate.__class__.__name__.lower()}:{aggregate.id}"
            data = snapshot.model_dump_json()
            
            # Save to Redis
            async with self._redis.pipeline() as pipe:
                await pipe.set(key, data)
                if self._ttl_seconds:
                    await pipe.expire(key, self._ttl_seconds)
                await pipe.execute()
                
        except Exception as e:
            self._logger.error("Error saving snapshot: %s", e, exc_info=True)
            raise SnapshotStoreError(f"Failed to save snapshot: {e}") from e
    
    async def delete_snapshot(
        self,
        aggregate_type: Type[A],
        aggregate_id: UUID,
    ) -> None:
        """Delete a snapshot for an aggregate.
        
        Args:
            aggregate_type: The type of the aggregate
            aggregate_id: The ID of the aggregate
            
        Raises:
            SnapshotStoreError: If there's an error deleting the snapshot
        """
        if self._redis is None:
            raise SnapshotStoreError("Redis client not initialized")
            
        try:
            key = f"{self._prefix}{aggregate_type.__name__.lower()}:{aggregate_id}"
            await self._redis.delete(key)
            
        except Exception as e:
            self._logger.error("Error deleting snapshot: %s", e, exc_info=True)
            raise SnapshotStoreError(f"Failed to delete snapshot: {e}") from e
    
    @classmethod
    def get_snapshot_type(cls, aggregate_type: Type[A]) -> Type[S]:
        """Get the snapshot type for an aggregate type."""
        # This is a helper method that can be overridden by subclasses
        # to provide custom snapshot type resolution
        return cast(Type[S], getattr(aggregate_type, "__snapshot_type__", None))


class AggregateWithSnapshots(AggregateRoot[E]):
    """Mixin class for aggregates that support snapshots."""
    
    __snapshot_type__: Type[AggregateSnapshot]
    
    @classmethod
    def get_snapshot_type(cls) -> Type[AggregateSnapshot]:
        """Get the snapshot type for this aggregate."""
        return cls.__snapshot_type__
    
    @classmethod
    def create_snapshot(cls, aggregate: AggregateRoot[E]) -> AggregateSnapshot:
        """Create a snapshot of the aggregate's state."""
        return cls.__snapshot_type__.from_aggregate(aggregate)
    
    @classmethod
    def restore_from_snapshot(
        cls: Type[A],
        snapshot: AggregateSnapshot,
    ) -> A:
        """Restore an aggregate from a snapshot."""
        # This is a basic implementation that creates a new instance
        # and applies the snapshot data. Subclasses should override
        # to handle their specific state restoration.
        aggregate = cls.create()
        aggregate._id = snapshot.aggregate_id
        aggregate._version = snapshot.version
        aggregate._created_at = snapshot.created_at
        aggregate._updated_at = snapshot.updated_at
        return aggregate
