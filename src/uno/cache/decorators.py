"""Cache decorators for Uno."""

import asyncio
import functools
import inspect
from datetime import timedelta
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Optional,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from pydantic import BaseModel

from .cache import Cache, get_cache
from .protocols import CacheKey

T = TypeVar('T')
R = TypeVar('R')


def _make_key(
    func: Callable[..., R],
    args: Tuple[Any, ...],
    kwargs: Dict[str, Any],
    key_prefix: Optional[str] = None,
) -> CacheKey:
    """Generate a cache key from function arguments.
    
    Args:
        func: The function being decorated
        args: Positional arguments
        kwargs: Keyword arguments
        key_prefix: Optional key prefix
        
    Returns:
        A string key for the cache
    """
    # Get the function's parameter names
    sig = inspect.signature(func)
    bound_args = sig.bind(*args, **kwargs)
    bound_args.apply_defaults()
    
    # Create a key based on the function name and arguments
    key_parts = [key_prefix or func.__module__, func.__qualname__]
    
    # Add arguments to the key
    for name, value in bound_args.arguments.items():
        # Skip 'self' and 'cls' parameters
        if name in ('self', 'cls'):
            continue
            
        key_parts.append(f"{name}={_serialize_value(value)}")
    
    return ":".join(str(part) for part in key_parts)


def _serialize_value(value: Any) -> str:
    """Serialize a value for use in a cache key.
    
    Args:
        value: The value to serialize
        
    Returns:
        A string representation of the value
    """
    if value is None:
        return "None"
    elif isinstance(value, (str, int, float, bool)):
        return str(value)
    elif isinstance(value, BaseModel):
        # For Pydantic models, use their JSON representation
        return value.model_dump_json()
    elif hasattr(value, '__dict__'):
        # For objects with __dict__, use their dictionary representation
        return str(vars(value))
    else:
        # Fall back to string representation
        return str(value)


def cached(
    key_prefix: Optional[str] = None,
    ttl: Optional[Union[int, float, timedelta]] = None,
    cache: Optional[Cache[Any]] = None,
    cache_key_func: Optional[Callable[..., CacheKey]] = None,
) -> Callable[[Callable[..., R]], Callable[..., R]]:
    """Decorator to cache the result of a function.
    
    Args:
        key_prefix: Optional prefix for cache keys
        ttl: Time to live for cached values (in seconds or as timedelta)
        cache: Optional cache instance to use
        cache_key_func: Optional function to generate cache keys
        
    Returns:
        A decorator function
    """
    # Convert ttl to timedelta if it's a number
    if ttl is not None and not isinstance(ttl, timedelta):
        ttl = timedelta(seconds=float(ttl))
    
    def decorator(func: Callable[..., R]) -> Callable[..., R]:
        # Get the cache instance if not provided
        _cache = cache or get_cache()
        
        # Use the provided key function or the default one
        _cache_key_func = cache_key_func or (
            lambda *args, **kwargs: _make_key(func, args, kwargs, key_prefix)
        )
        
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> R:
            # Generate the cache key
            key = _cache_key_func(*args, **kwargs)
            
            try:
                # Try to get the result from the cache
                result = _cache.get(key)
                if result is not None:
                    return result
            except Exception as e:
                # If there's an error with the cache, log it but continue
                import logging
                logging.getLogger(__name__).warning(
                    "Cache get failed: %s", e, exc_info=True
                )
            
            # Call the original function
            result = func(*args, **kwargs)
            
            # Cache the result
            try:
                _cache.set(key, result, ttl=ttl)
            except Exception as e:
                # If there's an error with the cache, log it but continue
                import logging
                logging.getLogger(__name__).warning(
                    "Cache set failed: %s", e, exc_info=True
                )
            
            return result
        
        return wrapper
    
    return decorator


def cached_async(
    key_prefix: Optional[str] = None,
    ttl: Optional[Union[int, float, timedelta]] = None,
    cache: Optional[Cache[Any]] = None,
    cache_key_func: Optional[Callable[..., CacheKey]] = None,
) -> Callable[[Callable[..., Awaitable[R]]], Callable[..., Awaitable[R]]]:
    """Decorator to cache the result of an async function.
    
    Args:
        key_prefix: Optional prefix for cache keys
        ttl: Time to live for cached values (in seconds or as timedelta)
        cache: Optional cache instance to use
        cache_key_func: Optional function to generate cache keys
        
    Returns:
        A decorator function
    """
    # Convert ttl to timedelta if it's a number
    if ttl is not None and not isinstance(ttl, timedelta):
        ttl = timedelta(seconds=float(ttl))
    
    def decorator(func: Callable[..., Awaitable[R]]) -> Callable[..., Awaitable[R]]:
        # Get the cache instance if not provided
        _cache = cache or get_cache()
        
        # Use the provided key function or the default one
        _cache_key_func = cache_key_func or (
            lambda *args, **kwargs: _make_key(func, args, kwargs, key_prefix)
        )
        
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> R:
            # Generate the cache key
            key = _cache_key_func(*args, **kwargs)
            
            try:
                # Try to get the result from the cache
                result = await _cache.get(key)
                if result is not None:
                    return result
            except Exception as e:
                # If there's an error with the cache, log it but continue
                import logging
                logging.getLogger(__name__).warning(
                    "Cache get failed: %s", e, exc_info=True
                )
            
            # Call the original function
            result = await func(*args, **kwargs)
            
            # Cache the result
            try:
                await _cache.set(key, result, ttl=ttl)
            except Exception as e:
                # If there's an error with the cache, log it but continue
                import logging
                logging.getLogger(__name__).warning(
                    "Cache set failed: %s", e, exc_info=True
                )
            
            return result
        
        return wrapper
    
    return decorator
