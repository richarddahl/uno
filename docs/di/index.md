# Dependency Injection System Developer Documentation

The Uno Framework provides a robust dependency injection (DI) system that helps manage object creation, lifetime, and dependencies. This document explains how to use and extend the DI system in your applications.

## Key Features

* **Loose Coupling**: Reduce dependencies between components and make your code more modular and testable.
* **Inversion of Control**: Let the container manage object creation and lifetime, making it easier to switch between different implementations.
* **Extensive Configuration Options**: Customize the DI system to fit your needs, from simple to complex scenarios.

## Architecture

The Uno DI system consists of the following components:

* **ServiceCollection**: A registry for all available services.
* **ServiceContainer**: Handles resolving services based on their registered interfaces and lifetimes.
* **ServiceScope**: Manages the lifetime of services within a specific scope.

## Terminology Note

> **Note:** In this documentation, the term "service" refers to any class or object managed by the dependency injection (DI) container, such as repositories, loggers, or domain services. This usage is standard in DI frameworks. In contrast, in Domain-Driven Design (DDD), a "domain service" is a specific pattern for encapsulating domain logic that doesn't naturally fit within an Entity or Value Object. If you are building DDD-style applications, be mindful of this distinction: "service" in the DI context is a broader term and may include both domain and infrastructure-level components.

## Core Concepts

### Service Lifetimes

The DI system supports three service lifetimes:

1. **Singleton**: A single instance is created and shared throughout the application
2. **Scoped**: A new instance is created for each scope (e.g., per request)
3. **Transient**: A new instance is created each time the service is resolved

### Service Registration

Services are registered with the `ServiceCollection` class, which acts as a registry for all available services.

### Service Resolution

The `ServiceContainer` and `ServiceScope` classes handle resolving services based on their registered interfaces and lifetimes.

## Basic Usage

### Setting Up the DI Container

```python
from uno.core.di import ServiceCollection, ServiceContainer
from myapp.services import Logger, ConsoleLogger, Database, PostgresDatabase

# Create a service collection
services = ServiceCollection()

# Register services with different lifetimes
services.add_singleton(Logger, ConsoleLogger)  # Interface, Implementation
services.add_scoped(Database, PostgresDatabase)
services.add_transient(EmailSender)  # Self-implementing service

# Initialize the container
ServiceContainer.initialize(services)
```

### Resolving Services

```python
# Get a singleton service
logger = ServiceContainer.resolve(Logger)
logger.info("Application started")

# Using scoped services
with ServiceContainer.create_scope() as scope:
    db = scope.resolve(Database)
    users = db.query("SELECT * FROM users")
    
    # Nested dependencies are automatically resolved
    user_service = scope.resolve(UserService)  # UserService depends on Database
```

## Advanced Features

### Factory Registration

For complex object creation or when you need more control over instantiation:

```python
services.add_factory(ComplexObject, lambda service_provider: ComplexObject(
    dependency1=service_provider.resolve(Dependency1),
    dependency2=service_provider.resolve(Dependency2),
    config_value="some_value"
))
```

### Conditional Registration

Register different implementations based on environment or configuration:

```python
if app_config.environment == "production":
    services.add_singleton(EmailService, ProductionEmailService)
else:
    services.add_singleton(EmailService, DevelopmentEmailService)
```

### Lazy Resolution

When you want to defer service instantiation until actually needed:

```python
# Get a lazy reference
lazy_service = ServiceContainer.resolve_lazy(ExpensiveService)

# Later in the code
if condition:
    actual_service = lazy_service.value  # Only resolved when accessed
```

### Async Support

For services that require async initialization or disposal:

```python
async with ServiceContainer.create_async_scope() as scope:
    db = await scope.resolve_async(AsyncDatabase)
    results = await db.query("SELECT * FROM users")
```

## Implementing Services

### Protocol-Based Interfaces

Use Python's Protocol classes to define service interfaces:

```python
from typing import Protocol

class Logger(Protocol):
    def info(self, message: str) -> None: ...
    def error(self, message: str, exception: Exception = None) -> None: ...

class ConsoleLogger:
    def info(self, message: str) -> None:
        print(f"INFO: {message}")
        
    def error(self, message: str, exception: Exception = None) -> None:
        print(f"ERROR: {message}")
        if exception:
            print(f"Exception: {exception}")
```

### Disposable Services

For services that need cleanup:

```python
from uno.core.di import Disposable

class DatabaseConnection(Disposable):
    def __init__(self, connection_string: str):
        self.connection = create_connection(connection_string)
    
    def dispose(self) -> None:
        self.connection.close()
        
    # For async disposal
    async def dispose_async(self) -> None:
        await self.connection.close_async()
```

## Best Practices

1. **Register by Interface**: Always register services by their interface, not their implementation
2. **Minimize Service Scope**: Use the narrowest scope necessary for your services
3. **Dispose Resources**: Implement the Disposable interface for services that manage resources
4. **Avoid Service Locator**: Inject dependencies directly rather than resolving them inside methods
5. **Keep Services Focused**: Each service should have a single responsibility

## Extending the DI System

### Custom Service Providers

You can create custom service providers by implementing the `ServiceProvider` interface:

```python
from uno.core.di import ServiceProvider

class CustomServiceProvider(ServiceProvider):
    def resolve(self, service_type):
        # Custom resolution logic
        pass
```

### Middleware for Service Resolution

You can add middleware to intercept service resolution:

```python
from uno.core.di import ServiceResolutionMiddleware

class LoggingMiddleware(ServiceResolutionMiddleware):
    def resolve(self, service_type, next):
        print(f"Resolving service: {service_type.__name__}")
        return next(service_type)

# Register middleware
ServiceContainer.add_middleware(LoggingMiddleware())
```

## Troubleshooting

### Circular Dependencies

The DI system will detect circular dependencies at runtime. To resolve:

1. Refactor your services to break the circular dependency
2. Use factory methods to defer one side of the dependency
3. Use event-based communication between the services

### Missing Dependencies

If you get a `DependencyResolutionError`, check:

1. That all required services are registered
2. That implementations correctly implement their interfaces
3. That you're resolving from the correct scope

## API Reference

### ServiceCollection

- `add_singleton(service_type, implementation_type=None)`
- `add_scoped(service_type, implementation_type=None)`
- `add_transient(service_type, implementation_type=None)`
- `add_factory(service_type, factory_func)`

### ServiceContainer

- `initialize(service_collection)`
- `resolve(service_type)`
- `resolve_lazy(service_type)`
- `create_scope()`
- `create_async_scope()`

### ServiceScope

- `resolve(service_type)`
- `resolve_async(service_type)`
- `dispose()`
- `dispose_async()`