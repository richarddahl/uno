"""In-memory backend for the cache system."""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple, TypeVar, Union

from uno.cache.cache import CacheBackend, CacheStats
from uno.errors import CacheBackendError, CacheMissError
from uno.logging import LoggerProtocol, get_logger
from uno.metrics import measure_time

T = TypeVar('T')


class MemoryBackend(CacheBackend[T]):
    """In-memory cache backend."""
    
    def __init__(
        self,
        namespace: str = "default",
        default_ttl: Optional[timedelta] = None,
        max_size: Optional[int] = 1000,
        metrics: Optional[Any] = None,
        logger: Optional[LoggerProtocol] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the in-memory cache backend.
        
        Args:
            namespace: Cache namespace to avoid key collisions
            default_ttl: Default time-to-live for cached values
            max_size: Maximum number of items the cache can hold
            metrics: Metrics client for collecting cache metrics
            logger: Logger instance (optional)
            **kwargs: Additional arguments (ignored)
        """
        super().__init__(
            namespace=namespace,
            default_ttl=default_ttl,
            max_size=max_size,
            metrics=metrics,
            logger=logger,
        )
        
        # Use OrderedDict for LRU eviction
        self._store: Dict[str, Tuple[T, Optional[float]]] = OrderedDict()
        self._lock = asyncio.Lock()
    
    async def _get(self, key: str) -> T:
        """Get a value from the cache."""
        async with self._lock:
            if key not in self._store:
                raise CacheMissError(f"Key not found: {key}")
            
            value, expiry = self._store[key]
            
            # Check if the item has expired
            if expiry is not None and time.time() > expiry:
                del self._store[key]
                raise CacheMissError(f"Key expired: {key}")
            
            # Move the key to the end to mark it as recently used
            self._store.move_to_end(key)
            
            return value
    
    async def _set(
        self,
        key: str,
        value: T,
        ttl: Optional[timedelta] = None,
    ) -> None:
        """Set a value in the cache."""
        async with self._lock:
            # If the key already exists, remove it first to update its position
            if key in self._store:
                del self._store[key]
            
            # Calculate expiry time
            expiry = (time.time() + ttl.total_seconds()) if ttl else None
            
            # Add the new item
            self._store[key] = (value, expiry)
            
            # If we've exceeded max_size, remove the least recently used item
            if self.max_size is not None and len(self._store) > self.max_size:
                # Remove the first item (least recently used)
                self._store.popitem(last=False)
    
    async def _delete(self, key: str) -> bool:
        """Delete a value from the cache."""
        async with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False
    
    async def _clear(self) -> None:
        """Clear all values from the cache."""
        async with self._lock:
            self._store.clear()
    
    async def _get_stats(self) -> CacheStats:
        """Get cache statistics."""
        stats = CacheStats(self.max_size)
        
        async with self._lock:
            # Count items and check for expired ones
            current_time = time.time()
            expired_count = 0
            
            for key, (_, expiry) in list(self._store.items()):
                if expiry is not None and current_time > expiry:
                    expired_count += 1
            
            # Update stats
            stats._size = len(self._store)
            stats._hits = stats.hits  # Preserve existing hits
            stats._misses = stats.misses  # Preserve existing misses
            
            # If we have expired items, clean them up
            if expired_count > 0:
                await self._cleanup()
        
        return stats
    
    async def _cleanup(self) -> None:
        """Clean up expired items from the cache."""
        async with self._lock:
            current_time = time.time()
            expired_keys = [
                key
                for key, (_, expiry) in self._store.items()
                if expiry is not None and current_time > expiry
            ]
            
            for key in expired_keys:
                del self._store[key]
    
    async def close(self) -> None:
        """Clean up resources."""
        # Nothing to do for in-memory cache
        pass
    
    async def __aenter__(self) -> 'MemoryBackend[T]':
        """Context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()
