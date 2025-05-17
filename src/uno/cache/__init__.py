"""Caching utilities for Uno.

This module provides a flexible and extensible caching system with the following features:

- Support for multiple backends (in-memory, Redis, etc.)
- Type-safe API with protocol-based interfaces
- Decorators for easy function result caching
- Support for time-based expiration
- Namespacing to prevent key collisions
- Metrics and statistics collection
- Thread-safe and asyncio-compatible
- Dependency injection support

Example usage:

    # Basic usage with dependency injection
    from uno.injection import get_container
    from uno.cache import CacheProtocol, cache_module
    
    # Configure the container with the cache module
    container = get_container()
    container.install(cache_module())
    
    # Get a cache instance
    cache = container.get(CacheProtocol)
    
    # Set a value
    await cache.set("key", "value", ttl=3600)  # 1 hour TTL
    
    # Get a value
    value = await cache.get("key")
    
    # Using the decorator
    from uno.cache import cached
    
    @cached(ttl=300)  # Cache for 5 minutes
    def expensive_operation(x: int) -> int:
        return x * x

    # Async version
    from uno.cache import cached_async
    
    @cached_async(ttl=300)
    async def async_expensive_operation(x: int) -> int:
        return x * x

    # Using Redis backend with custom settings
    from uno.cache import CacheSettings, cache_module
    
    settings = CacheSettings(
        CACHE_BACKEND="redis",
        REDIS_URL="redis://localhost:6379/0",
        CACHE_DEFAULT_TTL=3600,  # 1 hour
    )
    
    container.install(cache_module(settings))
"""

from .cache import Cache, CacheBackend, CacheStats
from .decorators import cached, cached_async
from .protocols import (
    CacheKey,
    CacheValue,
    CacheProtocol,
    CacheBackendProtocol,
    CacheStatsProtocol,
)
from .errors import (
    CacheError,
    CacheMissError,
    CacheBackendError,
    CacheSerializationError,
    CacheConfigurationError,
)
from .backends import MemoryBackend, RedisBackend
from .config import CacheSettings
from .injection import cache_module, get_cache
from .logging import CacheLogger

# Re-export for convenience
__all__ = [
    # Core classes
    'Cache',
    'CacheBackend',
    'CacheStats',
    'CacheLogger',
    'CacheSettings',
    
    # Protocols
    'CacheKey',
    'CacheValue',
    'CacheProtocol',
    'CacheBackendProtocol',
    'CacheStatsProtocol',
    
    # Decorators
    'cached',
    'cached_async',
    
    # Errors
    'CacheError',
    'CacheMissError',
    'CacheBackendError',
    'CacheSerializationError',
    'CacheConfigurationError',
    
    # Backends
    'MemoryBackend',
    'RedisBackend',
    
    # Dependency injection
    'cache_module',
    'get_cache',
]
