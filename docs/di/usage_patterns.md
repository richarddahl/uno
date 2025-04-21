# Dependency Injection Usage Patterns

This document outlines common patterns and best practices for using the Uno framework's dependency injection system effectively.

## Basic Setup Pattern

The most common pattern for setting up the DI container is:

```python
from uno.core.di import ServiceCollection, initialize_container
from uno.core.di.provider import ServiceProvider

# Create services collection
services = ServiceCollection()

# Configure services
services.add_singleton(ConfigService)
services.add_scoped(UserService, UserServiceImpl)
services.add_transient(EmailSender)

# Initialize the container
container = initialize_container(services)

# Optional: Create a provider for lifecycle management
provider = ServiceProvider()
provider.configure_from_collection(services)
await provider.initialize()
```

## Service Registration Patterns

### Constructor Injection

The most common pattern is constructor injection, where dependencies are passed to the constructor:

```python
class UserService:
    def __init__(self, db_service: DatabaseService, config: ConfigService):
        self.db_service = db_service
        self.config = config
        
# Register it
services.add_scoped(UserService)
```

The DI container will automatically resolve `DatabaseService` and `ConfigService` when creating `UserService`.

### Interface/Implementation Separation

Register a service by its interface (Protocol) and provide the implementation:

```python
class UserServiceProtocol(Protocol):
    async def get_user(self, user_id: str) -> User: ...
    
class UserServiceImpl:
    def __init__(self, db: DatabaseProtocol):
        self.db = db
        
    async def get_user(self, user_id: str) -> User:
        # Implementation
        return await self.db.query_one(User, {"id": user_id})
        
# Register with interface-implementation separation
services.add_scoped(UserServiceProtocol, UserServiceImpl)
```

### Factory Functions

You can use factory functions for more complex initialization:

```python
def create_cache_service(config: ConfigService) -> CacheService:
    cache_type = config.get_value("cache_type", "memory")
    if cache_type == "redis":
        return RedisCacheService(config.get_value("redis_url"))
    else:
        return MemoryCacheService()
        
# Register factory function
services.add_singleton(CacheService, create_cache_service)
```

### Named Services with Type Variables

For multiple implementations of the same interface:

```python
FileStorageT = TypeVar('FileStorageT', bound=StorageService)
S3StorageT = TypeVar('S3StorageT', bound=StorageService)

services.add_singleton(StorageService[FileStorageT], FileStorageService)
services.add_singleton(StorageService[S3StorageT], S3StorageService)

# To resolve
file_storage = get_service(StorageService[FileStorageT])
s3_storage = get_service(StorageService[S3StorageT])
```

## Scope Management Patterns

### Using Scopes in Web Applications

In web applications, create a new scope for each request:

```python
@app.middleware("http")
async def di_middleware(request, call_next):
    async with create_async_scope() as scope:
        # Attach scope to request for later use
        request.state.di_scope = scope
        response = await call_next(request)
        return response
        
@app.get("/users/{user_id}")
async def get_user(user_id: str, request: Request):
    scope = request.state.di_scope
    user_service = scope.resolve(UserService)
    return await user_service.get_user(user_id)
```

### Using Scopes in Background Tasks

For background tasks, create a scope for the lifetime of the task:

```python
async def process_job(job_id: str):
    async with create_async_scope() as scope:
        job_processor = scope.resolve(JobProcessor)
        await job_processor.process(job_id)
```

### Manual Scope Management

For more control over scope lifetime:

```python
# Create a named scope
async with create_async_scope("transaction-123") as scope:
    user_service = scope.resolve(UserService)
    order_service = scope.resolve(OrderService)
    
    # Both services share the same scope
    await user_service.update_balance(user_id, -amount)
    await order_service.create_order(user_id, items)
```

## Lifecycle Management Patterns

### Services with Initialization and Cleanup

Implement the `ServiceLifecycle` interface for proper initialization and cleanup:

```python
from uno.core.di.provider import ServiceLifecycle

class DatabaseService(ServiceLifecycle):
    def __init__(self, config: ConfigService):
        self.config = config
        self.pool = None
        
    async def initialize(self) -> None:
        # Expensive operation done once
        self.pool = await create_connection_pool(
            self.config.get_value("db_url")
        )
        
    async def dispose(self) -> None:
        # Cleanup resources
        if self.pool:
            await self.pool.close()
```

### Using ServiceProvider for Automatic Lifecycle Management

The `ServiceProvider` automates lifecycle management:

```python
provider = ServiceProvider()

def configure(services):
    services.add_singleton(DatabaseService)
    services.add_singleton(CacheService)
    services.add_singleton(EventBus)
    
provider.configure_services(configure)

# Initialize all services in dependency order
await provider.initialize()

# Use the application...

# Shutdown - disposes services in reverse dependency order
await provider.dispose()
```

## Testing Patterns

### Mocking Dependencies

In tests, you can create a container with mocked dependencies:

```python
def test_user_service():
    # Create test container
    services = ServiceCollection()
    
    # Register mock dependencies
    mock_db = MockDatabase()
    services.add_instance(DatabaseProtocol, mock_db)
    
    # Register service to test
    services.add_scoped(UserService)
    
    # Initialize container
    container = initialize_container(services)
    
    # Resolve service with mocked dependencies
    user_service = get_service(UserService)
    
    # Test the service
    result = user_service.get_user("test-id")
    assert result.name == "Test User"
```

### Creating Test Scopes

For testing scoped services:

```python
def test_scoped_service():
    # Set up container
    services = ServiceCollection()
    services.add_scoped(ScopedService)
    initialize_container(services)
    
    # Create a test scope
    with create_scope("test-scope") as scope:
        service1 = scope.resolve(ScopedService)
        service2 = scope.resolve(ScopedService)
        
        # Same instance within a scope
        assert service1 is service2
```

## Best Practices

1. **Prefer constructor injection** over property or method injection
2. **Register services by interface** rather than concrete implementation
3. **Use the appropriate scope** for each service:
   - Singleton: For services with shared state or expensive to initialize
   - Scoped: For services that need to maintain state for a logical operation
   - Transient: For lightweight, stateless services
4. **Implement proper disposal** in services that acquire resources
5. **Create a new scope for each logical operation** (request, job, etc.)
6. **Avoid circular dependencies** between services
7. **Don't resolve services at module level** - wait until runtime to allow proper scope management
8. **Keep service initialization lightweight** if possible - use async initialization for expensive operations
9. **Don't store scopes for longer than needed** - dispose of them as soon as the operation completes