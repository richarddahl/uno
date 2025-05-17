"""Redis backend for the cache system."""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any, Dict, Optional, TypeVar, Union, cast

from redis.asyncio import Redis, RedisCluster
from redis.exceptions import RedisError

from uno.cache.cache import CacheBackend, CacheStats
from uno.errors import CacheBackendError, CacheMissError
from uno.logging import LoggerProtocol, get_logger
from uno.metrics import measure_time
from uno.serialization import get_serializer

T = TypeVar('T')


class RedisBackend(CacheBackend[T]):
    """Redis backend for the cache system."""
    
    def __init__(
        self,
        redis: Optional[Union[Redis, RedisCluster]] = None,
        namespace: str = "default",
        default_ttl: Optional[timedelta] = None,
        max_size: Optional[int] = None,
        metrics: Optional[Any] = None,
        logger: Optional[LoggerProtocol] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the Redis backend.
        
        Args:
            redis: Redis client instance. If not provided, a new one will be created.
            namespace: Cache namespace to avoid key collisions
            default_ttl: Default time-to-live for cached values
            max_size: Maximum number of items the cache can hold
            metrics: Metrics client for collecting cache metrics
            logger: Logger instance (optional)
            **kwargs: Additional arguments for the Redis client
        """
        super().__init__(
            namespace=namespace,
            default_ttl=default_ttl,
            max_size=max_size,
            metrics=metrics,
            logger=logger,
        )
        
        self._redis = redis or self._create_redis_client(**kwargs)
        self._serializer = get_serializer('json')
    
    def _create_redis_client(self, **kwargs: Any) -> Union[Redis, RedisCluster]:
        """Create a Redis client.
        
        Args:
            **kwargs: Arguments for the Redis client
            
        Returns:
            Redis or RedisCluster instance
            
        Raises:
            CacheBackendError: If the Redis client cannot be created
        """
        try:
            # Try to create a Redis client with the provided arguments
            # This is a simplified version - you might want to add more configuration options
            from redis.asyncio import Redis as AsyncRedis
            
            if 'url' in kwargs:
                return AsyncRedis.from_url(**kwargs)
            
            return AsyncRedis(
                host=kwargs.get('host', 'localhost'),
                port=kwargs.get('port', 6379),
                db=kwargs.get('db', 0),
                password=kwargs.get('password'),
                ssl=kwargs.get('ssl', False),
                **{k: v for k, v in kwargs.items() if k not in {'host', 'port', 'db', 'password', 'ssl'}},
            )
        except Exception as e:
            self._logger.error("Failed to create Redis client: %s", e, exc_info=True)
            raise CacheBackendError(f"Failed to create Redis client: {e}") from e
    
    async def _get(self, key: str) -> T:
        """Get a value from Redis."""
        try:
            data = await self._redis.get(key)
            if data is None:
                raise CacheMissError(f"Key not found: {key}")
            
            # Deserialize the value
            try:
                return self._serializer.deserialize(data, dict)  # type: ignore
            except Exception as e:
                self._logger.error("Failed to deserialize cached value: %s", e, exc_info=True)
                # If deserialization fails, treat it as a cache miss
                raise CacheMissError(f"Failed to deserialize cached value: {e}") from e
                
        except RedisError as e:
            self._logger.error("Redis error getting key %s: %s", key, e, exc_info=True)
            raise CacheBackendError(f"Redis error: {e}") from e
    
    async def _set(
        self,
        key: str,
        value: T,
        ttl: Optional[timedelta] = None,
    ) -> None:
        """Set a value in Redis."""
        try:
            # Serialize the value
            try:
                serialized = self._serializer.serialize(value)
            except Exception as e:
                self._logger.error("Failed to serialize value: %s", e, exc_info=True)
                raise CacheBackendError(f"Failed to serialize value: {e}") from e
            
            # Set the value in Redis
            ttl_seconds = int(ttl.total_seconds()) if ttl else None
            await self._redis.set(key, serialized, ex=ttl_seconds)
            
        except RedisError as e:
            self._logger.error("Redis error setting key %s: %s", key, e, exc_info=True)
            raise CacheBackendError(f"Redis error: {e}") from e
    
    async def _delete(self, key: str) -> bool:
        """Delete a value from Redis."""
        try:
            result = await self._redis.delete(key)
            return bool(result)
        except RedisError as e:
            self._logger.error("Redis error deleting key %s: %s", key, e, exc_info=True)
            raise CacheBackendError(f"Redis error: {e}") from e
    
    async def _clear(self) -> None:
        """Clear all values from Redis with the current namespace."""
        try:
            # This is a simple implementation that deletes all keys with the namespace prefix
            # In a production environment, you might want to use SCAN + DEL for large keysets
            pattern = f"{self.namespace}:*"
            keys = []
            async for key in self._redis.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                await self._redis.delete(*keys)
                
        except RedisError as e:
            self._logger.error("Redis error clearing cache: %s", e, exc_info=True)
            raise CacheBackendError(f"Redis error: {e}") from e
    
    async def _get_stats(self) -> CacheStats:
        """Get cache statistics from Redis."""
        stats = CacheStats(self.max_size)
        
        try:
            # This is a basic implementation - Redis doesn't provide detailed cache stats
            # like hits/misses by default. You might want to use Redis INFO command
            # or implement custom tracking for more detailed statistics.
            
            # Get the number of keys with the current namespace
            pattern = f"{self.namespace}:*"
            count = 0
            async for _ in self._redis.scan_iter(match=pattern, count=1000):
                count += 1
            
            # Update the stats
            stats._size = count
            
            # Note: Redis doesn't track hits/misses by default
            # You would need to implement this using Lua scripts or custom commands
            
        except RedisError as e:
            self._logger.error("Redis error getting stats: %s", e, exc_info=True)
        
        return stats
    
    async def close(self) -> None:
        """Close the Redis connection."""
        try:
            await self._redis.close()
        except Exception as e:
            self._logger.error("Error closing Redis connection: %s", e, exc_info=True)
    
    async def __aenter__(self) -> 'RedisBackend[T]':
        """Context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()
