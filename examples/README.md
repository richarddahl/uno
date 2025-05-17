# Cache System Examples

This directory contains examples of how to use the Uno cache system with dependency injection.

## Prerequisites

- Python 3.8+
- Uno framework installed
- For Redis backend: Redis server running locally or accessible via network

## Examples

### Basic Usage

The [cache_usage.py](cache_usage.py) example demonstrates:

1. Setting up the cache with dependency injection
2. Basic cache operations (get, set, delete)
3. Using the `@cached` and `@cached_async` decorators
4. Working with different cache backends (in-memory and Redis)

### Running the Example

1. Make sure you have the required dependencies:
   ```bash
   pip install "uno[redis]"  # For Redis backend support
   ```

2. Run the example:
   ```bash
   python -m examples.cache_usage
   ```

### Expected Output

```
=== Example 1: Basic Cache Usage ===
Cache miss for user 123, fetching from database...
User 1: {'id': '123', 'name': 'User 123', 'email': 'user123@example.com'}
Cache hit for user 123
User 1 (cached): {'id': '123', 'name': 'User 123', 'email': 'user123@example.com'}
Invalidated cache for user 123
Cache miss for user 123, fetching from database...
User 1 (refreshed): {'id': '123', 'name': 'User 123', 'email': 'user123@example.com'}

=== Example 2: Using @cached Decorator ===
Fetching product p100 from database...
Product 1: {'id': 'p100', 'name': 'Product p100', 'price': 99.99}
Product 1 (cached): {'id': 'p100', 'name': 'Product p100', 'price': 99.99}
Fetching product p200 from database (async)...
Product (async): {'id': 'p200', 'name': 'Product p200 (Async)', 'price': 89.99}

Cache Stats: CacheStats(hits=2, misses=2, size=3, max_size=1000)
```

## Configuration

You can configure the cache system using environment variables or by creating a `CacheSettings` instance:

```python
from uno.cache import CacheSettings

# Default settings (in-memory backend, 5-minute TTL)
settings = CacheSettings()

# Custom settings
custom_settings = CacheSettings(
    CACHE_BACKEND="redis",  # or "memory"
    REDIS_URL="redis://localhost:6379/0",
    CACHE_DEFAULT_TTL=300,  # 5 minutes
    CACHE_KEY_PREFIX="myapp:",
    CACHE_MAX_SIZE=1000,
)
```

### Environment Variables

You can also configure the cache using environment variables:

```bash
export CACHE_BACKEND=redis
export REDIS_URL=redis://localhost:6379/0
export CACHE_DEFAULT_TTL=300
export CACHE_KEY_PREFIX=myapp:
export CACHE_MAX_SIZE=1000
```

## Best Practices

1. **Use Meaningful Cache Keys**: Include the entity type and ID in your cache keys (e.g., `user:123`).

2. **Set Appropriate TTLs**: Balance between freshness and performance. Shorter TTLs for frequently changing data, longer for static data.

3. **Handle Cache Misses Gracefully**: Always handle the case where data isn't in the cache.

4. **Invalidate Cache When Needed**: Update or invalidate cache entries when the underlying data changes.

5. **Monitor Cache Performance**: Use the `get_stats()` method to monitor cache hit/miss ratios and adjust your caching strategy accordingly.

## Testing

To run the tests for the cache system:

```bash
hatch run test:testV
```

## License

This project is licensed under the terms of the MIT license.
