# Uno Framework DI Best Practices

This guide outlines best practices for using the Uno Framework's dependency injection system effectively. Following these practices will help you build more maintainable, testable, and robust applications.

## Architectural Patterns

### 1. Interface-First Design

Define service contracts using Protocol classes before implementing them:

```python
from typing import Protocol, List

class UserRepositoryProtocol(Protocol):
    async def get_user(self, user_id: str) -> dict: ...
    async def list_users(self) -> List[dict]: ...

# Then implement the protocol
class PostgresUserRepository:
    def __init__(self, db_provider):
        self.db_provider = db_provider
        
    async def get_user(self, user_id: str) -> dict:
        # Implementation
        pass
        
    async def list_users(self) -> List[dict]:
        # Implementation
        pass

# Register with the protocol as the service type
services.add_singleton(UserRepositoryProtocol, PostgresUserRepository)
```

This enables:
- Clear contract definitions
- Multiple implementations
- Easy mocking for tests

### 2. Service Layer Architecture

Organize services in layers:

```
application/
  ├─ services/      # Application services
  │   └─ user_service.py
  ├─ repositories/  # Data access layer
  │   └─ user_repository.py  
  └─ domain/        # Domain models
      └─ user.py
```

Register each layer appropriately:

```python
# Domain models (no DI needed)
# Repositories (data access)
services.add_scoped(UserRepositoryProtocol, PostgresUserRepository)
# Application services
services.add_singleton(UserServiceProtocol, UserService)
```

### 3. Factory Pattern for Complex Creation

Use factory services for complex object creation:

```python
class ReportFactoryProtocol(Protocol):
    def create_report(self, report_type: str, **params) -> Report: ...

class ReportFactory:
    def __init__(self, template_provider, data_provider):
        self.template_provider = template_provider
        self.data_provider = data_provider
        
    def create_report(self, report_type: str, **params) -> Report:
        template = self.template_provider.get_template(report_type)
        data = self.data_provider.get_data(**params)
        return Report(template, data)

services.add_singleton(ReportFactoryProtocol, ReportFactory)
```

### 4. Composition Root Pattern

Register all dependencies at the application's entry point:

```python
# In app_startup.py
async def configure_services():
    services = ServiceCollection()
    
    # Register core services
    services.add_singleton(LoggerProtocol, ConsoleLogger)
    services.add_singleton(ConfigProtocol, AppConfig)
    
    # Register data access
    services.add_scoped(DatabaseProviderProtocol, PostgresProvider)
    services.add_scoped(UserRepositoryProtocol, UserRepository)
    
    # Register application services
    services.add_singleton(UserServiceProtocol, UserService)
    
    # Configure and initialize
    provider = get_service_provider()
    provider.configure_services(services)
    await initialize_services()
```

## Service Lifetime Guidelines

### When to Use Singleton

Use singleton scope for:
- Stateless services
- Configuration providers
- Logging services
- Service factories
- Global managers
- Cached resources

```python
# Stateless services
services.add_singleton(EmailFormatter)
services.add_singleton(PasswordHasher)

# Configuration and logging
services.add_singleton(ConfigProtocol, EnvConfig)
services.add_singleton(LoggerProtocol, StructuredLogger)

# Global managers
services.add_singleton(CacheManager)
services.add_singleton(MetricsCollector)
```

### When to Use Scoped

Use scoped services for:
- Database connections
- Request-specific context
- User context
- Per-request caches
- Transaction managers

```python
# Database connections
services.add_scoped(DatabaseConnection)

# Request context
services.add_scoped(UserContext)
services.add_scoped(RequestMetadata)

# Transaction managers
services.add_scoped(TransactionManager)
```

### When to Use Transient

Use transient scope for:
- Short-lived objects
- Services with no shared state
- Resource-intensive services
- Disposable operations

```python
# Disposable operations
services.add_transient(FileUploader)
services.add_transient(ReportGenerator)

# Non-shared models
services.add_transient(ValidationContext)
```

## Anti-Patterns to Avoid

### 1. Service Locator Anti-Pattern

**Avoid:**
```python
# Directly accessing the service provider within business logic
class UserService:
    def __init__(self):
        # Anti-pattern: Direct dependency on service provider
        self.provider = get_service_provider()
    
    def process_user(self, user_id):
        # Anti-pattern: Resolving dependencies at runtime
        repository = self.provider.get_service(UserRepository)
        return repository.get_user(user_id)
```

**Better:**
```python
class UserService:
    def __init__(self, repository: UserRepositoryProtocol):
        # Proper constructor injection
        self.repository = repository
    
    def process_user(self, user_id):
        return self.repository.get_user(user_id)
```

### 2. Circular Dependencies

**Avoid:**
```python
# Class A depends on Class B
class ServiceA:
    def __init__(self, service_b: 'ServiceB'):
        self.service_b = service_b

# Class B depends on Class A
class ServiceB:
    def __init__(self, service_a: ServiceA):
        self.service_a = service_a
```

**Better:**
```python
# Extract shared functionality to break the cycle
class SharedService:
    def common_functionality(self):
        pass

class ServiceA:
    def __init__(self, shared: SharedService):
        self.shared = shared

class ServiceB:
    def __init__(self, shared: SharedService):
        self.shared = shared
```

### 3. Overusing Singletons

**Avoid:**
```python
# Registering everything as singleton by default
services.add_singleton(UserRepository)  # Should be scoped
services.add_singleton(TransactionManager)  # Should be scoped
services.add_singleton(UserContext)  # Should be scoped
```

**Better:**
```python
# Use appropriate scopes
services.add_scoped(UserRepository)
services.add_scoped(TransactionManager)
services.add_scoped(UserContext)
services.add_singleton(ConfigService)  # Stateless, can be singleton
```

### 4. Concrete Class Coupling

**Avoid:**
```python
# Direct dependency on concrete class
class UserService:
    def __init__(self, repository: PostgresUserRepository):
        self.repository = repository
```

**Better:**
```python
# Depend on abstraction
class UserService:
    def __init__(self, repository: UserRepositoryProtocol):
        self.repository = repository
```

## Testing with DI

### 1. Unit Testing with Mock Services

```python
from unittest.mock import Mock

def test_user_service():
    # Create mock repository
    mock_repository = Mock(spec=UserRepositoryProtocol)
    mock_repository.get_user.return_value = {"id": "123", "name": "Test User"}
    
    # Create service with mock dependency
    service = UserService(repository=mock_repository)
    
    # Test the service
    result = service.process_user("123")
    
    # Verify result and interactions
    assert result["name"] == "Test User"
    mock_repository.get_user.assert_called_once_with("123")
```

### 2. Integration Testing with Test Container

```python
def test_user_flow_integration():
    # Create test services
    services = ServiceCollection()
    
    # Register real implementations with test configurations
    services.add_singleton(ConfigProtocol, TestConfig)
    services.add_scoped(DatabaseProviderProtocol, TestDatabaseProvider)
    services.add_scoped(UserRepositoryProtocol, UserRepository)
    services.add_singleton(UserServiceProtocol, UserService)
    
    # Build resolver and get service
    resolver = services.build()
    user_service = resolver.resolve(UserServiceProtocol)
    
    # Run test with real implementation but test database
    with resolver.create_scope() as scope:
        repository = scope.resolve(UserRepositoryProtocol)
        # Set up test data
        repository.create_user({"id": "test1", "name": "Test User"})
        
        # Test the service
        result = user_service.process_user("test1")
        assert result["name"] == "Test User"
```

### 3. Mocking Scoped Services

```python
def test_with_scoped_services():
    # Set up mocks
    mock_db = Mock(spec=DatabaseConnection)
    mock_context = Mock(spec=UserContext)
    
    # Create test services
    services = ServiceCollection()
    services.add_instance(DatabaseConnection, mock_db)
    services.add_instance(UserContext, mock_context)
    services.add_singleton(UserService)
    
    # Create custom scope
    resolver = services.build()
    with resolver.create_scope() as scope:
        # Get service
        service = scope.resolve(UserService)
        
        # Test
        service.process()
        
        # Verify
        mock_db.execute.assert_called_once()
```

## Resource Management

### 1. Proper Initialization

Services requiring initialization should implement `ServiceLifecycle`:

```python
from uno.core.di.provider import ServiceLifecycle

class DatabaseService(ServiceLifecycle):
    def __init__(self, config: ConfigProtocol):
        self.config = config
        self.pool = None
        
    async def initialize(self) -> None:
        connection_string = self.config.get_value("DATABASE_URL")
        self.pool = await create_connection_pool(
            connection_string,
            min_connections=5,
            max_connections=20
        )
        
    async def dispose(self) -> None:
        if self.pool:
            await self.pool.close()
```

Register lifecycle services:

```python
provider.register_lifecycle_service(DatabaseService)
```

### 2. Scoped Resource Cleanup

Scoped services with resources should implement cleanup methods:

```python
class RequestScope:
    def __init__(self, connection: DatabaseConnection):
        self.connection = connection
        self.transaction = None
        
    async def begin(self):
        self.transaction = await self.connection.begin()
        
    async def dispose(self):
        if self.transaction:
            try:
                await self.transaction.rollback()
            except:
                pass
```

The DI system will call `dispose()` automatically when the scope ends.

## Performance Optimization

### 1. Lazy Resolution

For expensive services, consider using factories and lazy initialization:

```python
def create_expensive_service(config: ConfigProtocol):
    # Only created when actually needed
    return ExpensiveService(
        config.get_value("service_url"),
        timeout=config.get_value("timeout", 30)
    )

services.add_singleton(ExpensiveServiceProtocol, create_expensive_service)
```

### 2. Scope Reuse

Reuse scopes when possible instead of creating new ones:

```python
# Process multiple items in a single scope
async with resolver.create_async_scope() as scope:
    db = scope.resolve(DatabaseConnection)
    
    for item in items:
        # Reuse the same db connection
        await process_item(item, db)
```

### 3. Profile Service Resolution

During development, enable debug logging to identify slow service resolution:

```python
import logging
logging.getLogger("uno.di").setLevel(logging.DEBUG)
```

## Documentation Best Practices

### 1. Document Service Dependencies

```python
class UserService:
    """User management service.
    
    Dependencies:
        - UserRepositoryProtocol: For user data access
        - LoggerProtocol: For logging operations
        - ConfigProtocol: For service configuration
    """
    def __init__(
        self, 
        repository: UserRepositoryProtocol,
        logger: LoggerProtocol,
        config: ConfigProtocol
    ):
        self.repository = repository
        self.logger = logger
        self.config = config
```

### 2. Document Service Lifecycle

```python
class DatabaseService(ServiceLifecycle):
    """Database connection provider.
    
    Lifecycle:
        - initialize(): Creates connection pool based on configuration
        - dispose(): Closes all connections in the pool
    
    Dependencies:
        - ConfigProtocol: For database configuration
    """
    # ...
```

### 3. Document Registration Requirements

```python
class UserModule:
    """User management module.
    
    Registration:
        - Requires DatabaseProviderProtocol to be registered
        - Requires ConfigProtocol to be registered
        - Registers UserRepositoryProtocol as scoped
        - Registers UserServiceProtocol as singleton
    
    Example:
        services.add_singleton(UserServiceProtocol, UserService)
        services.add_scoped(UserRepositoryProtocol, UserRepository)
    """
    # ...
```

## Conclusion

Following these best practices will help you use the Uno Framework's DI system effectively and avoid common pitfalls. Remember that dependency injection is a means to an end: it helps you write more maintainable, testable, and modular code.

Key takeaways:
1. Use appropriate service lifetimes
2. Prefer constructor injection
3. Design with interfaces (Protocols)
4. Implement proper resource management
5. Test with mock dependencies
6. Document service requirements and lifecycle