# Uno Framework DI Components Reference

This document provides a detailed reference of the key components in the Uno Framework's dependency injection system. Each component is explained with its purpose, methods, and usage examples.

## ServiceCollection

`ServiceCollection` provides a fluent API for configuring service registrations. It's the primary configuration point for the DI system.

### Methods

| Method | Description |
|--------|-------------|
| `add_singleton(service_type, implementation=None, **params)` | Register a singleton service |
| `add_scoped(service_type, implementation=None, **params)` | Register a scoped service |
| `add_transient(service_type, implementation=None, **params)` | Register a transient service |
| `add_instance(service_type, instance)` | Register an existing instance as a singleton |
| `build(logger=None)` | Build a ServiceResolver with the configured services |

### Example

```python
services = ServiceCollection()

# Register a singleton with the same implementation type
services.add_singleton(Logger)

# Register a singleton with a specific implementation
services.add_singleton(LoggerProtocol, ConsoleLogger)

# Register with constructor parameters
services.add_singleton(
    ConfigService, 
    config_path="settings.json", 
    environment="production"
)

# Register an existing instance
logger = ConsoleLogger()
services.add_instance(LoggerProtocol, logger)

# Build a resolver
resolver = services.build()
```

## ServiceRegistration

`ServiceRegistration` holds the configuration for how a service should be resolved, including its implementation type or factory, scope, and initialization parameters.

### Properties

| Property | Description |
|----------|-------------|
| `implementation` | The implementation type or factory function |
| `scope` | The service lifetime scope (ServiceScope enum) |
| `params` | Parameters to pass to the constructor/factory |

### Usage

This class is typically used internally by the ServiceCollection and ServiceResolver, but can be created directly if needed:

```python
from uno.core.di.container import ServiceRegistration, ServiceScope

# Create a registration for a singleton service
registration = ServiceRegistration(
    implementation=ConsoleLogger,
    scope=ServiceScope.SINGLETON,
    params={"log_level": "INFO"}
)
```

## ServiceScope

`ServiceScope` is an enum that defines the lifetime of registered services.

### Values

| Value | Description |
|-------|-------------|
| `SINGLETON` | One instance per container, shared across the application |
| `SCOPED` | One instance per scope (e.g., per request), created when first requested in a scope |
| `TRANSIENT` | New instance each time the service is resolved |

### Example

```python
from uno.core.di.container import ServiceScope

# Register services with different scopes
services.add_singleton(LoggerProtocol, ConsoleLogger)  # Default is SINGLETON
services.add_scoped(DatabaseProtocol, PostgresDatabase)  # SCOPED
services.add_transient(EmailSender)  # TRANSIENT
```

## ServiceResolver

`ServiceResolver` is the core resolution engine that manages service instances and dependencies. It handles the creation of singleton, scoped, and transient instances, and provides scope management.

### Methods

| Method | Description |
|--------|-------------|
| `register(service_type, implementation, scope=ServiceScope.SINGLETON, params=None)` | Register a service |
| `register_instance(service_type, instance)` | Register an existing instance as a singleton |
| `resolve(service_type)` | Resolve a service instance |
| `create_scope(scope_id=None)` | Create a synchronous service scope |
| `create_async_scope(scope_id=None)` | Create an asynchronous service scope |

### Example

```python
# Resolve a singleton service
logger = resolver.resolve(Logger)

# Using scopes for scoped services
with resolver.create_scope() as scope:
    db = scope.resolve(DatabaseConnection)
    # db is scoped to this context
    
# Async scope
async with resolver.create_async_scope() as scope:
    db = scope.resolve(DatabaseConnection)
    # Async disposal happens automatically
```

## ServiceProvider

`ServiceProvider` is a global access point and lifecycle manager for services. It wraps the service resolver and provides additional functionality for extensions and lifecycle management.

### Methods

| Method | Description |
|--------|-------------|
| `configure_services(services)` | Configure the base services |
| `register_extension(name, services)` | Register a service extension |
| `register_lifecycle_service(service_type)` | Register a service that requires lifecycle management |
| `is_initialized()` | Check if the provider has been initialized |
| `initialize()` | Initialize the provider and all registered services |
| `shutdown()` | Shut down the provider and dispose all services |
| `get_service(service_type)` | Get a service by its type |
| Convenience methods | `get_config()`, `get_db_provider()`, etc. |

### Example

```python
from uno.core.di import get_service_provider, initialize_services, shutdown_services

# Get the provider singleton
provider = get_service_provider()

# Configure services
provider.configure_services(services)

# Initialize
await initialize_services()

# Get services
logger = provider.get_service(Logger)
config = provider.get_config()

# Shutdown
await shutdown_services()
```

## ServiceLifecycle

`ServiceLifecycle` is an interface for services that need custom initialization and disposal.

### Methods

| Method | Description |
|--------|-------------|
| `initialize()` | Initialize the service asynchronously |
| `dispose()` | Dispose the service asynchronously |

### Example

```python
from uno.core.di.provider import ServiceLifecycle

class DatabaseService(ServiceLifecycle):
    def __init__(self, config):
        self.config = config
        self.pool = None
        
    async def initialize(self) -> None:
        # Initialize resources
        self.pool = await create_connection_pool(self.config.get_connection_string())
        
    async def dispose(self) -> None:
        # Clean up resources
        if self.pool:
            await self.pool.close()

# Register the service
services.add_singleton(DatabaseService)

# Register for lifecycle management
provider.register_lifecycle_service(DatabaseService)
```

## Global Functions

The DI system provides several global functions for convenience:

### get_service_provider()

Returns the global service provider singleton instance.

```python
from uno.core.di import get_service_provider

provider = get_service_provider()
```

### initialize_services()

Initializes all services, including base services and extensions.

```python
from uno.core.di import initialize_services

async def startup():
    await initialize_services()
```

### shutdown_services()

Shuts down all services, disposing resources in the reverse order of initialization.

```python
from uno.core.di import shutdown_services

async def cleanup():
    await shutdown_services()
```

### register_singleton()

Registers a singleton instance directly with the global service provider.

```python
from uno.core.di import register_singleton

result = register_singleton(LoggerProtocol, console_logger)
if result.is_error():
    print(f"Failed to register: {result.error}")
```

## Discovery Utilities

The DI system includes utilities for discovering and registering services automatically:

### framework_service Decorator

```python
from uno.core.di.decorators import framework_service
from uno.core.di.container import ServiceScope

@framework_service(service_type=RepositoryProtocol, scope=ServiceScope.SCOPED)
class UserRepository:
    def __init__(self, db_provider):
        self.db_provider = db_provider
```

### discover_services Function

```python
from uno.core.di.discovery import discover_services

# Find all services in a package
services = discover_services("myapp.features")
```

### register_services_in_package Function

```python
from uno.core.di.discovery import register_services_in_package

# Register all services in a package
register_services_in_package("myapp.features", provider)
```

### scan_directory_for_services Function

```python
from uno.core.di.discovery import scan_directory_for_services

# Scan a directory for packages containing services
scan_directory_for_services("/path/to/modules", "myapp.plugins", provider)
```

## Advanced Configuration

### Dependency Resolution with Constructor Parameters

```python
# Register with explicit params
services.add_singleton(
    UserService,
    db_provider=custom_db_provider,
    logger=custom_logger
)

# Automatic dependency resolution
services.add_singleton(UserService)  # Dependencies resolved from constructor types
```

### Extension Registration

```python
# Create extension services
auth_services = ServiceCollection()
auth_services.add_singleton(AuthManager)
auth_services.add_scoped(UserContext)

# Register with the provider
provider.register_extension("auth", auth_services)
```

### Protocol-Based Service Resolution

```python
from typing import Protocol

class EmailServiceProtocol(Protocol):
    def send(self, to: str, subject: str, body: str) -> bool: ...

class SMTPEmailService:
    def send(self, to: str, subject: str, body: str) -> bool:
        # Implementation
        return True

# Register using the protocol
services.add_singleton(EmailServiceProtocol, SMTPEmailService)

# Resolve using the protocol
email_service = provider.get_service(EmailServiceProtocol)
email_service.send("user@example.com", "Hello", "Message body")
```
