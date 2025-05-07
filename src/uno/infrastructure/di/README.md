# Uno Dependency Injection System

The Uno Dependency Injection (DI) system is a powerful, type-safe, and feature-rich dependency injection framework designed for building robust and maintainable applications. This document provides an overview of the system and its key features.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core Concepts](#core-concepts)
3. [Service Registration](#service-registration)
4. [Service Scopes](#service-scopes)
5. [Service Configuration](#service-configuration)
6. [Service Lifecycle](#service-lifecycle)
7. [Service Events](#service-events)
8. [Service Versioning](#service-versioning)
9. [Service Composition](#service-composition)
10. [Service Constraints](#service-constraints)
11. [Best Practices](#best-practices)

## Quick Start

```python
from uno.infrastructure.di.decorators import service, singleton
from uno.infrastructure.di.service_scope import ServiceScope

# Define an interface
class IMessageService(Protocol):
    async def send_message(self, message: str) -> None:
        ...

# Implement the service
@service(interface=IMessageService, scope=ServiceScope.SINGLETON)
class MessageService:
    async def send_message(self, message: str) -> None:
        print(f"Sending message: {message}")

# Or use the convenience decorator
@singleton(interface=IMessageService)
class AnotherMessageService:
    async def send_message(self, message: str) -> None:
        print(f"Sending message: {message}")
```

## Core Concepts

The DI system is built around several core concepts:

1. **Services**: Classes that provide functionality to your application
2. **Interfaces**: Contracts that services must implement
3. **Scopes**: Lifetime management for service instances
4. **Dependencies**: Services that other services depend on
5. **Configuration**: Options and settings for services
6. **Lifecycle**: Service initialization and cleanup
7. **Events**: Service state changes and notifications
8. **Versioning**: Service version management
9. **Composition**: Combining multiple services
10. **Constraints**: Service requirements and validations

## Service Registration

Services can be registered using decorators:

```python
# Basic service registration
@service
class MyService:
    pass

# Service with interface
@service(interface=IMyService)
class MyService:
    pass

# Service with scope
@service(scope=ServiceScope.SINGLETON)
class MyService:
    pass

# Service with configuration
@service(options_type=MyServiceOptions)
class MyService:
    pass
```

## Service Scopes

The system supports three service scopes:

1. **Singleton**: One instance for the entire application
2. **Scoped**: One instance per scope
3. **Transient**: New instance for each request

```python
# Singleton service
@singleton
class MyService:
    pass

# Scoped service
@scoped
class MyService:
    pass

# Transient service
@transient
class MyService:
    pass
```

## Service Configuration

Services can be configured using options:

```python
@dataclass
class DatabaseOptions(ServiceOptions):
    connection_string: str
    max_pool_size: int = 10
    timeout: int = 30

    def validate(self) -> None:
        if not self.connection_string:
            raise ServiceConfigurationError("Connection string is required")
        if self.max_pool_size < 1:
            raise ServiceConfigurationError("Max pool size must be positive")

@service(options_type=DatabaseOptions)
class DatabaseService:
    def __init__(self, options: DatabaseOptions):
        self.options = options
```

## Service Lifecycle

Services can implement lifecycle management:

```python
@service(requires_initialization=True, requires_cleanup=True)
class MyService(ServiceLifecycle):
    async def initialize(self) -> None:
        # Initialize service
        pass

    async def start(self) -> None:
        # Start service
        pass

    async def stop(self) -> None:
        # Stop service
        pass

    async def cleanup(self) -> None:
        # Clean up resources
        pass
```

## Service Events

Services can emit and handle events:

```python
class MyEventHandler(ServiceEventHandler):
    async def handle_event(self, event: ServiceEvent) -> None:
        if event.type == ServiceEventType.HEALTH_CHANGED:
            # Handle health change
            pass

@service(event_handlers=[MyEventHandler()])
class MyService:
    async def initialize(self) -> None:
        await self.event_emitter.emit_event(ServiceEvent(
            type=ServiceEventType.INITIALIZED,
            source=self.__class__.__name__
        ))
```

## Service Versioning

Services can be versioned:

```python
@service(version="1.2.3")
class MyService:
    pass

# With prerelease/build metadata
@service(version="1.2.3-beta.1+build.123")
class MyService:
    pass
```

## Service Composition

Services can be composed:

```python
@service(composite=MyCompositeService)
class MyService:
    def compose(self, services: List[Any]) -> MyService:
        # Combine services
        return self
```

## Service Constraints

Services can have constraints:

```python
class MyConstraintValidator(ServiceConstraintValidator):
    def validate(self, service_type: Type[Any], dependencies: Set[Type[Any]]) -> None:
        # Validate constraints
        pass

@service(
    constraints={ServiceConstraint.REQUIRED_DEPENDENCY},
    constraint_validators=[MyConstraintValidator()]
)
class MyService:
    pass
```

## Best Practices

1. **Use Interfaces**: Always define interfaces for your services
2. **Choose Appropriate Scopes**: Use the right scope for your services
3. **Validate Configuration**: Always validate service options
4. **Handle Lifecycle**: Implement lifecycle methods when needed
5. **Use Events**: Emit events for important state changes
6. **Version Services**: Keep track of service versions
7. **Compose Services**: Use composition for complex services
8. **Add Constraints**: Add constraints to ensure service requirements
9. **Handle Errors**: Properly handle and report errors
10. **Document Services**: Document service behavior and requirements

## Additional Resources

- [Service Collection Documentation](service_collection.md)
- [Service Provider Documentation](service_provider.md)
- [Service Scope Documentation](service_scope.md)
- [Error Handling Documentation](errors.md)
- [Examples](examples/) 