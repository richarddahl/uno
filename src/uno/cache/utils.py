"""Utility functions for the cache system."""

import asyncio
from datetime import timedelta
from typing import Any, Dict, Optional, Union

from redis.asyncio import Redis, RedisCluster

from uno.config import settings
from uno.logging import LoggerProtocol, get_logger


def get_redis_connection(
    url: Optional[str] = None,
    **kwargs: Any,
) -> Union[Redis, RedisCluster]:
    """Get a Redis connection.
    
    Args:
        url: Redis connection URL (e.g., 'redis://localhost:6379/0')
        **kwargs: Additional arguments for the Redis client
        
    Returns:
        Redis or RedisCluster instance
        
    Raises:
        RuntimeError: If the Redis client cannot be created
    """
    logger = get_logger("uno.cache.redis")
    
    try:
        from redis.asyncio import Redis as AsyncRedis
        
        # Use URL if provided, otherwise use settings
        redis_url = url or settings.REDIS_URL
        
        if not redis_url:
            raise ValueError("Redis URL not provided and REDIS_URL is not set in settings")
        
        # Create the Redis client
        if redis_url.startswith(('redis://', 'rediss://', 'unix://')):
            # Use URL-based connection
            client = AsyncRedis.from_url(
                redis_url,
                **kwargs,
            )
        else:
            # Fall back to host/port configuration
            client = AsyncRedis(
                host=kwargs.get('host', 'localhost'),
                port=kwargs.get('port', 6379),
                db=kwargs.get('db', 0),
                password=kwargs.get('password'),
                ssl=kwargs.get('ssl', False),
                **{k: v for k, v in kwargs.items() 
                   if k not in {'host', 'port', 'db', 'password', 'ssl'}},
            )
        
        return client
        
    except ImportError:
        logger.error("Redis client not installed. Install with: pip install redis")
        raise RuntimeError("Redis client not installed. Install with: pip install redis")
    except Exception as e:
        logger.error("Failed to create Redis client: %s", e, exc_info=True)
        raise RuntimeError(f"Failed to create Redis client: {e}") from e


async def check_redis_connection(client: Union[Redis, RedisCluster], timeout: float = 1.0) -> bool:
    """Check if the Redis connection is working.
    
    Args:
        client: Redis client instance
        timeout: Maximum time to wait for the ping to complete
        
    Returns:
        True if the connection is working, False otherwise
    """
    try:
        # Use asyncio.wait_for to add a timeout
        await asyncio.wait_for(client.ping(), timeout=timeout)
        return True
    except (asyncio.TimeoutError, Exception):
        return False


def parse_ttl(ttl: Optional[Union[int, float, timedelta]]) -> Optional[timedelta]:
    """Parse a TTL value into a timedelta.
    
    Args:
        ttl: TTL value (seconds as int/float, or timedelta)
        
    Returns:
        Timedelta or None if ttl is None
    """
    if ttl is None:
        return None
    elif isinstance(ttl, (int, float)):
        return timedelta(seconds=float(ttl))
    elif isinstance(ttl, timedelta):
        return ttl
    else:
        raise ValueError(f"Invalid TTL value: {ttl}. Expected int, float, or timedelta.")


def get_cache_config(prefix: str = "CACHE_") -> Dict[str, Any]:
    """Get cache configuration from settings with the given prefix.
    
    Args:
        prefix: Prefix for cache-related settings
        
    Returns:
        Dictionary of cache configuration
    """
    from uno.config import settings
    
    config = {}
    
    # Get all settings that start with the prefix
    for key, value in settings.dict().items():
        if key.startswith(prefix):
            # Remove the prefix and convert to lowercase
            config_key = key[len(prefix):].lower()
            config[config_key] = value
    
    return config
