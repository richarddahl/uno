# Uno Framework Dependency Injection

This directory implements a modern, hierarchical dependency injection system for the Uno framework, featuring service lifecycle management, scoped service resolution, automatic dependency discovery, and both synchronous and asynchronous context management.

## Terminology Note

> **Note:** In this documentation, the term "service" refers to any class or object managed by the dependency injection (DI) container, such as repositories, loggers, or domain services. This usage is standard in DI frameworks. In contrast, in Domain-Driven Design (DDD), a "domain service" is a specific pattern for encapsulating domain logic that doesn't naturally fit within an Entity or Value Object. If you are building DDD-style applications, be mindful of this distinction: "service" in the DI context is a broader term and may include both domain and infrastructure-level components.

## Architecture Overview

The DI system consists of several key components:

- **ServiceCollection**: Fluent API for configuring service registrations
- **ServiceResolver**: Core resolution engine that manages instances and dependencies
- **ServiceProvider**: Global access point and lifecycle manager for services
- **ServiceRegistration**: Configuration for how a service should be resolved
- **ServiceLifecycle**: Interface for services that need custom initialization/disposal

## Service Lifetime Scopes

The DI system supports three service lifetime scopes:

- **Singleton**: One instance per container, shared across the application
- **Scoped**: One instance per scope (e.g., per request), created when first requested in a scope
- **Transient**: New instance each time the service is resolved

## Basic Usage

### Registering Services

```python
# Create a service collection
services = ServiceCollection()

# Register services with different lifetimes
services.add_singleton(Logger, ConsoleLogger)
services.add_scoped(DatabaseConnection, PostgresConnection)
services.add_transient(EmailSender)

# Register an existing instance
logger = ConsoleLogger()
services.add_instance(Logger, logger)

# Register with constructor parameters
services.add_singleton(
    ConfigService, 
    config_path="settings.json", 
    environment="production"
)
```

### Configuring and Initializing the Service Provider

```python
from uno.core.di import get_service_provider, initialize_services

# Configure base services
provider = get_service_provider()
provider.configure_services(services)

# Register an extension (optional)
provider.register_extension("myfeature", feature_services)

# Initialize all services
await initialize_services()
```

### Resolving Services

```python
# Get the service provider
provider = get_service_provider()

# Resolve a service
logger = provider.get_service(Logger)
logger.info("Application started")

# Convenience methods for common services
config = provider.get_config()
db_provider = provider.get_db_provider()
```

### Using Scoped Services

```python
# Create a scope for scoped services
resolver = provider.get_service(ServiceResolver)
with resolver.create_scope() as scope:
    # Resolve scoped services
    db = scope.resolve(DatabaseConnection)
    # db is scoped to this context and will be disposed automatically
    
# For async contexts
async with resolver.create_async_scope() as scope:
    db = scope.resolve(DatabaseConnection)
    await db.execute_query(...)
    # Async disposal will happen automatically
```

## Service Discovery

The DI system includes automatic service discovery through decorators:

```python
from uno.core.di.decorators import framework_service
from uno.core.di.container import ServiceScope

@framework_service(scope=ServiceScope.SINGLETON)
class MyService:
    def __init__(self, logger: Logger):
        self.logger = logger
        
    def process(self, data):
        self.logger.info("Processing data...")
```

Discover and register services from a package:

```python
from uno.core.di.discovery import discover_services, register_services_in_package

# Discover and register services from a package
register_services_in_package("myapp.features", provider)

# Or scan a directory
scan_directory_for_services("/path/to/modules", "myapp.plugins", provider)
```

## Service Lifecycle Management

For services that need custom initialization and disposal:

```python
from uno.core.di.provider import ServiceLifecycle

class DatabaseService(ServiceLifecycle):
    async def initialize(self) -> None:
        # Set up connections, initialize resources
        await self.pool.initialize()
        
    async def dispose(self) -> None:
        # Clean up resources
        await self.pool.close()

# Register as a lifecycle service
provider.register_lifecycle_service(DatabaseService)
```

Lifecycle services are automatically initialized during `initialize_services()` and disposed during `shutdown_services()`.

## Application Startup and Shutdown

```python
from uno.core.di import initialize_services, shutdown_services

async def startup():
    # Initialize all services
    await initialize_services()
    
async def shutdown():
    # Properly dispose all services
    await shutdown_services()
```

## Protocol-Based Dependency Injection

Use Protocol classes to define service interfaces:

```python
from typing import Protocol

class LoggerProtocol(Protocol):
    def info(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...

# Register implementation
services.add_singleton(LoggerProtocol, ConsoleLogger)

# Resolve using the protocol
logger = provider.get_service(LoggerProtocol)
```

This enables loose coupling and easier testing through interface-based programming.

## Advanced Usage: Extensions

The DI system supports modular extensions:

```python
# Create extension services
auth_services = ServiceCollection()
auth_services.add_singleton(AuthManager)
auth_services.add_scoped(UserContext)

# Register with the provider
provider.register_extension("auth", auth_services)
```

## Production Tips

1. Register services early in the application lifecycle
2. Prefer singleton scope for stateless services
3. Use scoped services for request-specific state
4. Implement ServiceLifecycle for proper resource management
5. Use protocol-based dependencies for better testability
6. Use decorators for automatic registration
