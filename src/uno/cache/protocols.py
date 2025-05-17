"""Protocols for the caching system."""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, Generic, Optional, Protocol, TypeVar, runtime_checkable

from uno.metrics import MetricsProtocol

# Type variables for cache keys and values
CacheKey = str
CacheValue = TypeVar('CacheValue')


@runtime_checkable
class CacheStatsProtocol(Protocol):
    """Protocol for cache statistics."""
    
    @property
    @abstractmethod
    def hits(self) -> int:
        """Number of cache hits."""
        ...
    
    @property
    @abstractmethod
    def misses(self) -> int:
        """Number of cache misses."""
        ...
    
    @property
    @abstractmethod
    def size(self) -> int:
        """Current number of items in the cache."""
        ...
    
    @property
    @abstractmethod
    def max_size(self) -> Optional[int]:
        """Maximum number of items the cache can hold."""
        ...
    
    @abstractmethod
    def record_hit(self) -> None:
        """Record a cache hit."""
        ...
    
    @abstractmethod
    def record_miss(self) -> None:
        """Record a cache miss."""
        ...
    
    @abstractmethod
    def increment_size(self, delta: int = 1) -> None:
        """Increment the cache size."""
        ...
    
    @abstractmethod
    def decrement_size(self, delta: int = 1) -> None:
        """Decrement the cache size."""
        ...
    
    def hit_ratio(self) -> float:
        """Calculate the cache hit ratio."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


@runtime_checkable
class CacheBackendProtocol(Protocol, Generic[CacheValue]):
    """Protocol for cache backends."""
    
    @abstractmethod
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
        ...
    
    @abstractmethod
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
        ...
    
    @abstractmethod
    async def delete(self, key: CacheKey) -> bool:
        """Delete a value from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            True if the key was in the cache, False otherwise
            
        Raises:
            CacheBackendError: If there's an error accessing the cache
        """
        ...
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear all values from the cache.
        
        Raises:
            CacheBackendError: If there's an error accessing the cache
        """
        ...
    
    @abstractmethod
    async def get_stats(self) -> CacheStatsProtocol:
        """Get cache statistics.
        
        Returns:
            Cache statistics
        """
        ...


@runtime_checkable
class CacheProtocol(Protocol, Generic[CacheValue]):
    """Protocol for cache implementations."""
    
    @property
    @abstractmethod
    def namespace(self) -> str:
        """Cache namespace."""
        ...
    
    @abstractmethod
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
        ...
    
    @abstractmethod
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
        ...
    
    @abstractmethod
    async def delete(self, key: CacheKey) -> bool:
        """Delete a value from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            True if the key was in the cache, False otherwise
        """
        ...
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear all values from the cache."""
        ...
    
    @abstractmethod
    def with_namespace(self, namespace: str) -> CacheProtocol[CacheValue]:
        """Create a new cache with a different namespace.
        
        Args:
            namespace: The new namespace
            
        Returns:
            A new cache instance with the specified namespace
        """
        ...
    
    @abstractmethod
    async def get_stats(self) -> CacheStatsProtocol:
        """Get cache statistics.
        
        Returns:
            Cache statistics
        """
        ...
