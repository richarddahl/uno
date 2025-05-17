"""Example usage of the Uno cache system with dependency injection."""

import asyncio
from datetime import timedelta

from uno.injection import get_container

# Import the cache module to register the cache components
from uno.cache import (
    CacheProtocol,
    CacheSettings,
    cache_module,
    cached,
    cached_async,
)


# Example service that uses caching
class UserService:
    def __init__(self, cache: CacheProtocol):
        self.cache = cache
    
    async def get_user(self, user_id: str) -> dict:
        """Get a user from cache or fall back to a slow operation."""
        cache_key = f"user:{user_id}"
        
        try:
            # Try to get from cache
            user = await self.cache.get(cache_key)
            print(f"Cache hit for user {user_id}")
            return user
        except KeyError:
            # Cache miss - simulate a slow operation
            print(f"Cache miss for user {user_id}, fetching from database...")
            await asyncio.sleep(0.5)  # Simulate database call
            
            # Create a fake user
            user = {
                "id": user_id,
                "name": f"User {user_id}",
                "email": f"user{user_id}@example.com",
            }
            
            # Cache the result for future use
            await self.cache.set(cache_key, user, ttl=timedelta(minutes=5))
            return user
    
    async def invalidate_user_cache(self, user_id: str) -> None:
        """Invalidate the cache for a specific user."""
        cache_key = f"user:{user_id}"
        await self.cache.delete(cache_key)
        print(f"Invalidated cache for user {user_id}")


# Example of using the @cached decorator
class ProductService:
    @cached(ttl=300)  # Cache for 5 minutes
    def get_product(self, product_id: str) -> dict:
        """Get product details with automatic caching."""
        print(f"Fetching product {product_id} from database...")
        # Simulate database call
        return {
            "id": product_id,
            "name": f"Product {product_id}",
            "price": 99.99,
        }
    
    @cached_async(ttl=300)  # Async version of the decorator
    async def get_product_async(self, product_id: str) -> dict:
        """Get product details with automatic caching (async version)."""
        print(f"Fetching product {product_id} from database (async)...")
        await asyncio.sleep(0.2)  # Simulate async database call
        return {
            "id": product_id,
            "name": f"Product {product_id} (Async)",
            "price": 89.99,
        }


async def main():
    # Configure the DI container
    container = get_container()
    
    # Configure cache with Redis backend
    settings = CacheSettings(
        CACHE_BACKEND="memory",  # Use "redis" for production
        CACHE_DEFAULT_TTL=300,  # 5 minutes
        CACHE_KEY_PREFIX="example:",
    )
    
    # Install the cache module with our settings
    container.install(cache_module(settings))
    
    # Get a cache instance
    cache = container.get(CacheProtocol)
    
    # Example 1: Basic cache usage
    print("=== Example 1: Basic Cache Usage ===")
    user_service = UserService(cache)
    
    # First call - cache miss
    user1 = await user_service.get_user("123")
    print(f"User 1: {user1}")
    
    # Second call - cache hit
    user1_cached = await user_service.get_user("123")
    print(f"User 1 (cached): {user1_cached}")
    
    # Invalidate cache
    await user_service.invalidate_user_cache("123")
    
    # Third call - cache miss again
    user1_refreshed = await user_service.get_user("123")
    print(f"User 1 (refreshed): {user1_refreshed}")
    
    # Example 2: Using @cached decorator
    print("\n=== Example 2: Using @cached Decorator ===")
    product_service = ProductService()
    
    # First call - cache miss
    product1 = product_service.get_product("p100")
    print(f"Product 1: {product1}")
    
    # Second call - cache hit
    product1_cached = product_service.get_product("p100")
    print(f"Product 1 (cached): {product1_cached}")
    
    # Async version
    product_async = await product_service.get_product_async("p200")
    print(f"Product (async): {product_async}")
    
    # Get cache stats
    stats = await cache.get_stats()
    print(f"\nCache Stats: {stats}")


if __name__ == "__main__":
    asyncio.run(main())
