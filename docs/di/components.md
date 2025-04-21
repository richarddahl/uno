# Dependency Injection Core Components

This document details the core components of the Uno framework's dependency injection system.

## ServiceCollection

`ServiceCollection` provides a fluent interface for configuring service registrations before building the container.

### Key Methods

| Method | Description |
|--------|-------------|
| `add_singleton(service_type, implementation=None, **params)` | Register a singleton service |
| `add_instance(service_type, instance)` | Register an existing instance as a singleton |
| `add_scoped(service_type, implementation=None, **params)` | Register a scoped service |
| `add_transient(service_type, implementation=None, **params)` | Register a transient service |
| `build(logger=None)` | Build a `ServiceResolver` from the collection |

### Example

```python
from uno.core.di import ServiceCollection
from myapp.services import UserService, UserServiceImpl, DatabaseService

services = ServiceCollection()
services.add_singleton(DatabaseService)
services.add_scoped(UserService, UserServiceImpl)
services.add_transient(EmailSender)
```

## ServiceScope

`ServiceScope` is an enum that defines the lifetime of registered services.

```python
class ServiceScope(Enum):
    """Service lifetime scopes for dependency injection."""
    SINGLETON = auto()  # One instance per container
    SCOPED = auto()     # One instance per scope (e.g., request)
    TRANSIENT = auto()  # New instance each time
```

## ServiceRegistration

`ServiceRegistration` holds the configuration for how a service should be resolved, including its implementation type or factory, scope, and initialization parameters.

```python
ServiceRegistration(
    implementation: type[T] | Callable[..., T],
    scope: ServiceScope = ServiceScope.SINGLETON,
    params: dict[str, Any] | None = None,
)
```

## ServiceResolver

`ServiceResolver` is responsible for resolving services based on their registrations, including handling dependencies and maintaining instance caches for different scopes.

### Key Methods

| Method | Description |
|--------|-------------|
| `register(service_type, implementation, scope, params=None)` | Register a service |
| `register_instance(service_type, instance)` | Register an existing instance |
| `resolve(service_type)` | Resolve a service instance |
| `create_scope(scope_id=None)` | Create a service scope (context manager) |
| `create_async_scope(scope_id=None)` | Create an async service scope (async context manager) |

### Example

```python
resolver = ServiceResolver()
resolver.register(UserService, UserServiceImpl, ServiceScope.SCOPED)

# Resolve a service
user_service = resolver.resolve(UserService)

# Create a scope
with resolver.create_scope() as scoped_resolver:
    scoped_service = scoped_resolver.resolve(ScopedService)
```

## ServiceContainer

`ServiceContainer` provides centralized access to the service resolver while avoiding the use of global variables.

### Key Methods

| Method | Description |
|--------|-------------|
| `initialize(services=None, logger=None)` | Initialize the container |
| `get()` | Get the container instance |
| `resolve(service_type)` | Resolve a service from the container |
| `create_scope(scope_id=None)` | Create a service scope |
| `create_async_scope(scope_id=None)` | Create an async service scope |

### Example

```python
from uno.core.di import ServiceContainer, ServiceCollection

# Initialize
services = ServiceCollection()
# ... configure services
ServiceContainer.initialize(services)

# Resolve
user_service = ServiceContainer.resolve(UserService)

# Create scope
with ServiceContainer.create_scope() as scope:
    scoped_service = scope.resolve(ScopedService)
```

## ServiceProvider

`ServiceProvider` provides a high-level API for managing services, including initialization and shutdown.

### Key Methods

| Method | Description |
|--------|-------------|
| `configure_services(configure_fn)` | Configure services using a callback |
| `initialize()` | Initialize the provider and all registered services |
| `dispose()` | Dispose all registered services |
| `get_service(service_type)` | Get a service from the provider |
| `create_scope(scope_id=None)` | Create a service scope |
| `create_async_scope(scope_id=None)` | Create an async service scope |

### Example

```python
from uno.core.di import ServiceProvider

provider = ServiceProvider()

# Configure services
def configure(services):
    services.add_singleton(ConfigService)
    services.add_scoped(UserService)
    
provider.configure_services(configure)

# Initialize
await provider.initialize()

# Get a service
config = provider.get_service(ConfigService)

# Create a scope
async with provider.create_async_scope() as scope:
    user_service = scope.resolve(UserService)

# Dispose (cleanup)
await provider.dispose()
```

## Module-Level Functions

The DI system also provides module-level convenience functions for direct access:

| Function | Description |
|----------|-------------|
| `initialize_container(services, logger=None)` | Initialize the container |
| `get_container()` | Get the container instance |
| `get_service(service_type)` | Resolve a service from the container |
| `create_scope(scope_id=None)` | Create a service scope |
| `create_async_scope(scope_id=None)` | Create an async service scope |

## Protocol Interfaces

The `interfaces.py` module defines Protocol classes that provide interfaces for various components in the framework, enabling dependency injection and improved testability. These include:

- `ConfigProtocol` - Interface for configuration providers
- `RepositoryProtocol` - Interface for data repositories
- `DatabaseProviderProtocol` - Interface for database providers
- `DBManagerProtocol` - Interface for database managers
- `ServiceProtocol` - Interface for service classes
- `DomainRepositoryProtocol` - Interface for domain repositories
- `DomainServiceProtocol` - Interface for domain services
- `EventBusProtocol` - Interface for event buses
- And many more

These Protocol classes define contracts that implementations must adhere to, allowing you to swap implementations without changing client code.