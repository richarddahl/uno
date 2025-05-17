"""Dependency injection setup for the cache system."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any, Callable, Optional, Type, TypeVar, cast

from uno.injection import Container, Module, provider, singleton
from uno.logging import LoggerProtocol, get_logger

from .backends.memory_backend import MemoryBackend
from .backends.redis_backend import RedisBackend
from .cache import Cache, CacheStats
from .config import CacheSettings
from .errors import CacheBackendError, CacheConfigurationError
from .logging import CacheLogger
from .protocols import (
    CacheBackendProtocol,
    CacheKey,
    CacheProtocol,
    CacheStatsProtocol,
    CacheValue,
)

T = TypeVar('T')


class CacheModule(Module):
    """Dependency injection module for the cache system."""
    
    def __init__(self, settings: Optional[CacheSettings] = None) -> None:
        """Initialize the cache module.
        
        Args:
            settings: Optional settings instance (uses default if None)
        """
        self.settings = settings or CacheSettings()
    
    def configure(self, container: Container) -> None:
        """Configure the cache module."""
        # Bind the cache backend based on configuration
        if self.settings.CACHE_BACKEND == "redis":
            container.bind(CacheBackendProtocol, self._create_redis_backend)
        else:
            container.bind(CacheBackendProtocol, self._create_memory_backend)
        
        # Bind the cache itself
        container.bind(CacheProtocol, self._create_cache)
        
        # Bind the cache logger
        container.bind(CacheLogger, self._create_cache_logger)
    
    @singleton
    @provider
    def _create_memory_backend(self) -> CacheBackendProtocol[Any]:
        """Create an in-memory cache backend."""
        return MemoryBackend(
            max_size=self.settings.CACHE_MAX_SIZE,
            default_ttl=self.settings.default_ttl_timedelta,
        )
    
    @singleton
    @provider
    def _create_redis_backend(self) -> CacheBackendProtocol[Any]:
        """Create a Redis cache backend."""
        if not self.settings.REDIS_URL:
            raise CacheConfigurationError(
                "Redis URL is required when using Redis backend",
                config_key="REDIS_URL",
            )
        
        try:
            from redis.asyncio import Redis
            
            client = Redis.from_url(
                self.settings.REDIS_URL,
                decode_responses=False,  # We handle serialization ourselves
            )
            
            return RedisBackend(
                client=client,
                key_prefix=self.settings.CACHE_KEY_PREFIX,
                default_ttl=self.settings.default_ttl_timedelta,
            )
        except ImportError as e:
            raise CacheConfigurationError(
                "Redis client is not installed. Install with: pip install redis",
                config_key="CACHE_BACKEND",
                cause=e,
            ) from e
        except Exception as e:
            raise CacheBackendError(
                f"Failed to initialize Redis backend: {str(e)}",
                backend="redis",
                cause=e,
            ) from e
    
    @singleton
    @provider
    def _create_cache(
        self,
        backend: CacheBackendProtocol[Any],
        logger: CacheLogger,
    ) -> CacheProtocol[Any]:
        """Create a cache instance."""
        return Cache(
            backend=backend,
            key_prefix=self.settings.CACHE_KEY_PREFIX,
            default_ttl=self.settings.default_ttl_timedelta,
            logger=logger,
        )
    
    @singleton
    @provider
    def _create_cache_logger(self) -> CacheLogger:
        """Create a cache logger instance."""
        return CacheLogger(name="uno.cache")


def get_cache(
    container: Optional[Container] = None,
    **overrides: Any,
) -> CacheProtocol[Any]:
    """Get a cache instance from the container.
    
    Args:
        container: Optional container to use (uses default if None)
        **overrides: Override any cache settings
        
    Returns:
        A configured cache instance
    """
    from uno.injection import get_container
    
    container = container or get_container()
    
    # Apply any overrides
    if overrides:
        settings = CacheSettings(**{
            **container.get(CacheSettings).model_dump(),
            **overrides,
        })
        
        # Create a child container with overridden settings
        child = container.create_child()
        child.bind(CacheSettings, lambda: settings)
        container = child
    
    return container.get(CacheProtocol)


def cache_module(settings: Optional[CacheSettings] = None) -> CacheModule:
    """Create a cache module with the given settings.
    
    Args:
        settings: Optional settings to use
        
    Returns:
        A configured CacheModule instance
    """
    return CacheModule(settings=settings)
