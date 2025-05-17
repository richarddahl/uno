# Uno Caching System

A flexible and extensible caching system for Uno, supporting multiple backends and designed for high performance and type safety.

## Features

- **Multiple Backends**: Supports in-memory and Redis backends out of the box
- **Type Safe**: Fully typed with Python's type hints
- **Async Support**: Built with asyncio in mind
- **Decorators**: Easy-to-use decorators for function result caching
- **Time-based Expiration**: Set TTL (time-to-live) for cached items
- **Namespacing**: Prevent key collisions with namespaces
- **Metrics**: Built-in support for collecting cache statistics
- **Thread-safe**: Safe to use in multi-threaded applications

## Installation

```bash
# For basic in-memory caching (no additional dependencies required)
pip install uno

# For Redis backend
pip install "uno[redis]"
```

## Quick Start

### Basic Usage

```python
from uno.cache import get_cache

# Get a cache instance with default in-memory backend
cache = get_cache()

# Set a value with a 1-hour TTL
await cache.set("user:123", {"name": "John Doe", "email": "john@example.com"}, ttl=3600)

# Get a value
user = await cache.get("user:123")
print(user)  # {'name': 'John Doe', 'email': 'john@example.com'}

# Delete a value
await cache.delete("user:123")

# Clear all cached values
await cache.clear()
```

### Using Decorators

```python
from datetime import timedelta
from uno.cache import cached, cached_async

# Cache the result of a sync function for 5 minutes
@cached(ttl=300)
def get_user_data(user_id: int) -> dict:
    # Expensive operation here
    return {"id": user_id, "name": f"User {user_id}"}

# Cache the result of an async function for 1 hour
@cached_async(ttl=timedelta(hours=1))
async def fetch_user_data(user_id: int) -> dict:
    # Async operation here
    return {"id": user_id, "name": f"User {user_id}"}
```

### Using Redis Backend

```python
from datetime import timedelta
from uno.cache import get_cache

# Create a Redis-backed cache
redis_cache = get_cache(
    backend="redis",
    url="redis://localhost:6379/0",
    default_ttl=timedelta(hours=1),
)

# Use it the same way as the in-memory cache
await redis_cache.set("key", "value")
value = await redis_cache.get("key")
```

## Configuration

The cache system can be configured using environment variables or directly in code:

### Environment Variables

```bash
# Cache backend (default: 'memory')
CACHE_BACKEND=redis

# Redis URL (required for Redis backend)
REDIS_URL=redis://localhost:6379/0

# Default TTL in seconds (optional)
CACHE_DEFAULT_TTL=3600

# Maximum size for in-memory cache (optional)
CACHE_MAX_SIZE=1000
```

### Programmatic Configuration

```python
from datetime import timedelta
from uno.cache import get_cache

cache = get_cache(
    backend="redis",
    url="redis://localhost:6379/0",
    default_ttl=timedelta(hours=1),
    max_size=1000,
    key_prefix="myapp:",
)
```

## API Reference

### Cache Methods

- `get(key: str, default: Any = None) -> Any`: Get a value from the cache
- `set(key: str, value: Any, ttl: Union[int, float, timedelta] = None) -> None`: Set a value in the cache
- `delete(key: str) -> bool`: Delete a value from the cache
- `clear() -> None`: Clear all values from the cache
- `get_stats() -> CacheStats`: Get cache statistics

### Decorators

- `@cached(ttl=None, key_prefix=None, cache=None)`: Cache the result of a sync function
- `@cached_async(ttl=None, key_prefix=None, cache=None)`: Cache the result of an async function

## Advanced Usage

### Custom Cache Keys

You can provide a custom key function to control how cache keys are generated:

```python
from uno.cache import cached

def custom_key_func(*args, **kwargs):
    # Custom key generation logic
    return f"custom:{args[0]}"

@cached(key_func=custom_key_func)
def get_user(user_id: int):
    return {"id": user_id}
```

### Cache Invalidation

```python
from uno.cache import get_cache

cache = get_cache()

# Set a value
await cache.set("user:123", {"name": "John"})

# Later, invalidate it
await cache.delete("user:123")
```

### Cache Statistics

```python
from uno.cache import get_cache

cache = get_cache()

# Get statistics
stats = await cache.get_stats()
print(f"Hits: {stats.hits}")
print(f"Misses: {stats.misses}")
print(f"Hit rate: {stats.hit_rate:.2%}")
print(f"Size: {stats.size}")
print(f"Max size: {stats.max_size}")
```

## Testing

To run the tests:

```bash
hatch run test:testV
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
