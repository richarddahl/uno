"""Cache implementation with pluggable backends."""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Generic, Optional, TypeVar, cast
from uuid import uuid4

from pydantic import BaseModel, Field

from uno.errors import CacheBackendError, CacheMissError
from uno.logging import LoggerProtocol, get_logger
from uno.metrics import measure_time
from uno.serialization import get_serializer

from .protocols import CacheKey, CacheValue, CacheProtocol, CacheBackendProtocol, CacheStatsProtocol

T = TypeVar('T')


class CacheStats(CacheStatsProtocol):
    """Cache statistics."""
    
    def __init__(self, max_size: Optional[int] = None) -> None:
        """Initialize cache statistics.
        
        Args:
            max_size: Maximum number of items the cache can hold
        """
        self._hits = 0
        self._misses = 0
        self._size = 0
        self._max_size = max_size
        self._lock = asyncio.Lock()
    
    @property
    def hits(self) -> int:
        """Number of cache hits."""
        return self._hits
    
    @property
    def misses(self) -> int:
        """Number of cache misses."""
        return self._misses
    
    @property
    def size(self) -> int:
        """Current number of items in the cache."""
        return self._size
    
    @property
    def max_size(self) -> Optional[int]:
        """Maximum number of items the cache can hold."""
        return self._max_size
    
    async def record_hit(self) -> None:
        """Record a cache hit."""
        async with self._lock:
            self._hits += 1
    
    async def record_miss(self) -> None:
        """Record a cache miss."""
        async with self._lock:
            self._misses += 1
    
    async def increment_size(self, delta: int = 1) -> None:
        """Increment the cache size."""
        async with self._lock:
            self._size += delta
    
    async def decrement_size(self, delta: int = 1) -> None:
        """Decrement the cache size."""
        async with self._lock:
            self._size = max(0, self._size - delta)
    
    def hit_ratio(self) -> float:
        """Calculate the cache hit ratio."""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0
    
    def __str__(self) -> str:
        """Return a string representation of the cache statistics."""
        return (
            f"CacheStats(hits={self.hits}, misses={self.misses}, "
            f"hit_ratio={self.hit_ratio():.2f}, size={self.size}, "
            f"max_size={self.max_size or 'unbounded'})"
        )


class CacheBackend(ABC, Generic[CacheValue]):
    """Abstract base class for cache backends."""
    
    def __init__(
        self,
        namespace: str = "default",
        default_ttl: Optional[timedelta] = None,
        max_size: Optional[int] = None,
        metrics: Optional[Any] = None,
        logger: Optional[LoggerProtocol] = None,
    ) -> None:
        """Initialize the cache backend.
        
        Args:
            namespace: Cache namespace to avoid key collisions
            default_ttl: Default time-to-live for cached values
            max_size: Maximum number of items the cache can hold
            metrics: Metrics client for collecting cache metrics
            logger: Logger instance (optional)
        """
        self.namespace = namespace
        self.default_ttl = default_ttl or timedelta(hours=1)
        self.max_size = max_size
        self.metrics = metrics
        self._logger = logger or get_logger(f"uno.cache.{self.__class__.__name__.lower()}")
        self._stats = CacheStats(max_size)
    
    @abstractmethod
    async def _get(self, key: str) -> CacheValue:
        """Get a value from the cache (implementation)."""
        ...
    
    @abstractmethod
    async def _set(
        self,
        key: str,
        value: CacheValue,
        ttl: Optional[timedelta] = None,
    ) -> None:
        """Set a value in the cache (implementation)."""
        ...
    
    @abstractmethod
    async def _delete(self, key: str) -> bool:
        """Delete a value from the cache (implementation)."""
        ...
    
    @abstractmethod
    async def _clear(self) -> None:
        """Clear all values from the cache (implementation)."""
        ...
    
    @abstractmethod
    async def _get_stats(self) -> CacheStats:
        """Get cache statistics (implementation)."""
        ...
    
    def _get_namespaced_key(self, key: CacheKey) -> str:
        """Get a namespaced cache key."""
        return f"{self.namespace}:{key}"
    
    @measure_time(namespace="cache")
    async def get(self, key: CacheKey) -> CacheValue:
        """Get a value from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            The cached value
            
        Raises:
            CacheMissError: If the key is not in the cache
            CacheBackendError: If there's an error accessing the cache
        """
        namespaced_key = self._get_namespaced_key(key)
        try:
            value = await self._get(namespaced_key)
            await self._stats.record_hit()
            return value
        except CacheMissError:
            await self._stats.record_miss()
            raise
        except Exception as e:
            self._logger.error("Error getting value from cache: %s", e, exc_info=True)
            raise CacheBackendError(f"Failed to get value from cache: {e}") from e
    
    @measure_time(namespace="cache")
    async def set(
        self,
        key: CacheKey,
        value: CacheValue,
        ttl: Optional[timedelta] = None,
    ) -> None:
        """Set a value in the cache.
        
        Args:
            key: The cache key
            value: The value to cache
            ttl: Time to live for the cached value
            
        Raises:
            CacheBackendError: If there's an error accessing the cache
        """
        namespaced_key = self._get_namespaced_key(key)
        try:
            await self._set(namespaced_key, value, ttl or self.default_ttl)
            await self._stats.increment_size()
        except Exception as e:
            self._logger.error("Error setting value in cache: %s", e, exc_info=True)
            raise CacheBackendError(f"Failed to set value in cache: {e}") from e
    
    @measure_time(namespace="cache")
    async def delete(self, key: CacheKey) -> bool:
        """Delete a value from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            True if the key was in the cache, False otherwise
            
        Raises:
            CacheBackendError: If there's an error accessing the cache
        """
        namespaced_key = self._get_namespaced_key(key)
        try:
            deleted = await self._delete(namespaced_key)
            if deleted:
                await self._stats.decrement_size()
            return deleted
        except Exception as e:
            self._logger.error("Error deleting value from cache: %s", e, exc_info=True)
            raise CacheBackendError(f"Failed to delete value from cache: {e}") from e
    
    @measure_time(namespace="cache")
    async def clear(self) -> None:
        """Clear all values from the cache.
        
        Raises:
            CacheBackendError: If there's an error accessing the cache
        """
        try:
            await self._clear()
            self._stats = CacheStats(self.max_size)
        except Exception as e:
            self._logger.error("Error clearing cache: %s", e, exc_info=True)
            raise CacheBackendError(f"Failed to clear cache: {e}") from e
    
    @measure_time(namespace="cache")
    async def get_stats(self) -> CacheStats:
        """Get cache statistics.
        
        Returns:
            Cache statistics
        """
        return await self._get_stats()


class Cache(CacheProtocol[CacheValue], Generic[CacheValue]):
    """Cache implementation with pluggable backends."""
    
    def __init__(
        self,
        backend: CacheBackendProtocol[CacheValue],
        namespace: str = "default",
        default_ttl: Optional[timedelta] = None,
        metrics: Optional[Any] = None,
        logger: Optional[LoggerProtocol] = None,
    ) -> None:
        """Initialize the cache.
        
        Args:
            backend: The cache backend to use
            namespace: Cache namespace to avoid key collisions
            default_ttl: Default time-to-live for cached values
            metrics: Metrics client for collecting cache metrics
            logger: Logger instance (optional)
        """
        self._backend = backend
        self._namespace = namespace
        self._default_ttl = default_ttl or timedelta(hours=1)
        self._metrics = metrics
        self._logger = logger or get_logger("uno.cache")
    
    @property
    def namespace(self) -> str:
        """Cache namespace."""
        return self._namespace
    
    @measure_time(namespace="cache")
    async def get(
        self,
        key: CacheKey,
        default: Any = None,
    ) -> CacheValue | Any:
        """Get a value from the cache.
        
        Args:
            key: The cache key
            default: Default value to return if key is not found
            
        Returns:
            The cached value or default if not found
        """
        try:
            return await self._backend.get(key)
        except CacheMissError:
            return default
        except Exception as e:
            self._logger.error("Error getting value from cache: %s", e, exc_info=True)
            return default
    
    @measure_time(namespace="cache")
    async def set(
        self,
        key: CacheKey,
        value: CacheValue,
        ttl: Optional[timedelta] = None,
    ) -> None:
        """Set a value in the cache.
        
        Args:
            key: The cache key
            value: The value to cache
            ttl: Time to live for the cached value
        """
        try:
            await self._backend.set(key, value, ttl or self._default_ttl)
        except Exception as e:
            self._logger.error("Error setting value in cache: %s", e, exc_info=True)
    
    @measure_time(namespace="cache")
    async def delete(self, key: CacheKey) -> bool:
        """Delete a value from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            True if the key was in the cache, False otherwise
        """
        try:
            return await self._backend.delete(key)
        except Exception as e:
            self._logger.error("Error deleting value from cache: %s", e, exc_info=True)
            return False
    
    @measure_time(namespace="cache")
    async def clear(self) -> None:
        """Clear all values from the cache."""
        try:
            await self._backend.clear()
        except Exception as e:
            self._logger.error("Error clearing cache: %s", e, exc_info=True)
    
    def with_namespace(self, namespace: str) -> Cache[CacheValue]:
        """Create a new cache with a different namespace.
        
        Args:
            namespace: The new namespace
            
        Returns:
            A new cache instance with the specified namespace
        """
        return Cache(
            backend=self._backend,
            namespace=namespace,
            default_ttl=self._default_ttl,
            metrics=self._metrics,
            logger=self._logger,
        )
    
    @measure_time(namespace="cache")
    async def get_stats(self) -> CacheStatsProtocol:
        """Get cache statistics.
        
        Returns:
            Cache statistics
        """
        try:
            return await self._backend.get_stats()
        except Exception as e:
            self._logger.error("Error getting cache stats: %s", e, exc_info=True)
            return CacheStats()


def get_cache(
    backend: str = "memory",
    namespace: str = "default",
    default_ttl: Optional[timedelta] = None,
    **kwargs: Any,
) -> Cache[Any]:
    """Get a cache instance with the specified backend.
    
    Args:
        backend: The cache backend to use ('memory', 'redis')
        namespace: Cache namespace to avoid key collisions
        default_ttl: Default time-to-live for cached values
        **kwargs: Additional backend-specific arguments
        
    Returns:
        A cache instance
        
    Raises:
        ValueError: If the backend is not supported
    """
    if backend == "memory":
        from .backends.memory_backend import MemoryBackend
        return Cache[Any](MemoryBackend(namespace=namespace, default_ttl=default_ttl, **kwargs))
    elif backend == "redis":
        from .backends.redis_backend import RedisBackend
        return Cache[Any](RedisBackend(namespace=namespace, default_ttl=default_ttl, **kwargs))
    else:
        raise ValueError(f"Unsupported cache backend: {backend}")
