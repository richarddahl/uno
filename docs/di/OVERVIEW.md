# Uno Dependency Injection System Overview

This document provides a detailed overview of the Uno Dependency Injection (DI) system, its architecture, and advanced features.

## Architecture

The DI system is built on several key components:

1. **Service Collection**: Manages service registration and configuration
2. **Service Provider**: Handles service resolution and lifecycle
3. **Service Scope**: Controls service lifetime
4. **Service Decorators**: Provides metadata and validation
5. **Service Events**: Enables event-driven communication
6. **Service Versioning**: Manages service compatibility
7. **Service Composition**: Supports service aggregation

## Service Collection

The `ServiceCollection` is the central registry for all services in the application. It provides:

- Service registration with different scopes
- Configuration management
- Dependency validation
- Service metadata tracking

Example:
```python
from uno.infrastructure.di.service_collection import ServiceCollection

services = ServiceCollection()

# Register services
services.add_singleton(IMessageService, MessageService)
services.add_scoped(IDatabaseService, DatabaseService)
services.add_transient(IEmailService, EmailService)

# Configure services
services.configure<DatabaseOptions>(lambda options: {
    "connection_string": "my-connection-string",
    "max_pool_size": 20
})
```

## Service Provider

The `ServiceProvider` is responsible for:

- Service resolution
- Dependency injection
- Lifecycle management
- Event handling
- Health monitoring

Example:
```python
from uno.infrastructure.di.service_provider import ServiceProvider

# Create service provider
provider = ServiceProvider(services)

# Resolve services
message_service = provider.get_service(IMessageService)
database_service = provider.get_service(IDatabaseService)

# Handle lifecycle
await provider.initialize_services()
await provider.start_services()
```

## Service Scopes

The system supports three service scopes:

1. **Singleton**:
   - One instance for the entire application
   - Shared state across all consumers
   - Suitable for stateless services

2. **Scoped**:
   - One instance per scope
   - State is isolated within the scope
   - Suitable for request-scoped services

3. **Transient**:
   - New instance for each request
   - No shared state
   - Suitable for lightweight services

Example:
```python
@singleton
class ConfigurationService:
    pass

@scoped
class UserSessionService:
    pass

@transient
class LoggingService:
    pass
```

## Service Configuration

Services can be configured using strongly-typed options:

```python
@dataclass
class EmailOptions(ServiceOptions):
    smtp_server: str
    port: int
    use_ssl: bool = True
    timeout: int = 30

    def validate(self) -> None:
        if not self.smtp_server:
            raise ServiceConfigurationError("SMTP server is required")
        if self.port < 1 or self.port > 65535:
            raise ServiceConfigurationError("Invalid port number")

@service(options_type=EmailOptions)
class EmailService:
    def __init__(self, options: EmailOptions):
        self.options = options
```

## Service Lifecycle

Services can implement the `ServiceLifecycle` protocol:

```python
@service(requires_initialization=True)
class DatabaseService(ServiceLifecycle):
    async def initialize(self) -> None:
        # Initialize database connection
        pass

    async def start(self) -> None:
        # Start database service
        pass

    async def pause(self) -> None:
        # Pause database service
        pass

    async def resume(self) -> None:
        # Resume database service
        pass

    async def stop(self) -> None:
        # Stop database service
        pass

    async def cleanup(self) -> None:
        # Clean up resources
        pass
```

## Service Events

The event system supports:

1. **Event Types**:
   - Service lifecycle events
   - Health status changes
   - State changes
   - Configuration changes

2. **Event Handlers**:
   - Async event processing
   - Event filtering
   - Event transformation

3. **Event Emitters**:
   - Async event emission
   - Event batching
   - Event persistence

Example:
```python
class DatabaseEventHandler(ServiceEventHandler):
    async def handle_event(self, event: ServiceEvent) -> None:
        if event.type == ServiceEventType.HEALTH_CHANGED:
            # Handle health change
            pass
        elif event.type == ServiceEventType.STATE_CHANGED:
            # Handle state change
            pass

@service(event_handlers=[DatabaseEventHandler()])
class DatabaseService:
    async def initialize(self) -> None:
        await self.event_emitter.emit_event(ServiceEvent(
            type=ServiceEventType.INITIALIZED,
            source=self.__class__.__name__
        ))
```

## Service Versioning

Services can be versioned using semantic versioning:

```python
@service(version="1.2.3")
class MyService:
    pass

# With prerelease
@service(version="1.2.3-beta.1")
class MyService:
    pass

# With build metadata
@service(version="1.2.3+build.123")
class MyService:
    pass
```

## Service Composition

Services can be composed using:

1. **Composite Services**:
   - Combine multiple services
   - Share functionality
   - Maintain separation of concerns

2. **Aggregate Services**:
   - Aggregate multiple services
   - Provide unified interface
   - Handle service coordination

Example:
```python
@service(composite=MessageCompositeService)
class MessageService:
    def compose(self, services: List[Any]) -> MessageService:
        # Combine services
        return self

@service(aggregate=NotificationAggregateService)
class NotificationService:
    def aggregate(self, services: List[Any]) -> NotificationService:
        # Aggregate services
        return self
```

## Service Constraints

Services can have constraints:

1. **Dependency Constraints**:
   - Required dependencies
   - Optional dependencies
   - Scope constraints

2. **Interface Constraints**:
   - Interface implementation
   - Method requirements
   - Type constraints

3. **Configuration Constraints**:
   - Required options
   - Option validation
   - Option dependencies

Example:
```python
class DatabaseConstraintValidator(ServiceConstraintValidator):
    def validate(self, service_type: Type[Any], dependencies: Set[Type[Any]]) -> None:
        # Validate database service constraints
        pass

@service(
    constraints={
        ServiceConstraint.REQUIRED_DEPENDENCY,
        ServiceConstraint.INTERFACE_IMPLEMENTATION
    },
    constraint_validators=[DatabaseConstraintValidator()]
)
class DatabaseService:
    pass
```

## Error Handling

The system provides comprehensive error handling:

1. **Service Errors**:
   - Registration errors
   - Resolution errors
   - Configuration errors

2. **Lifecycle Errors**:
   - Initialization errors
   - Start/stop errors
   - Cleanup errors

3. **Constraint Errors**:
   - Validation errors
   - Dependency errors
   - Interface errors

Example:
```python
try:
    services.add_singleton(IMessageService, MessageService)
except ServiceRegistrationError as e:
    # Handle registration error
    pass

try:
    await provider.initialize_services()
except ServiceLifecycleError as e:
    # Handle lifecycle error
    pass
```

## Best Practices

1. **Service Design**:
   - Use interfaces
   - Keep services focused
   - Follow SOLID principles

2. **Dependency Management**:
   - Minimize dependencies
   - Use appropriate scopes
   - Handle circular dependencies

3. **Configuration**:
   - Use strongly-typed options
   - Validate configuration
   - Use environment variables

4. **Lifecycle Management**:
   - Implement lifecycle methods
   - Handle errors properly
   - Clean up resources

5. **Event Handling**:
   - Use appropriate event types
   - Handle events asynchronously
   - Filter events when needed

6. **Versioning**:
   - Follow semantic versioning
   - Document breaking changes
   - Test version compatibility

7. **Composition**:
   - Use composition over inheritance
   - Keep composites simple
   - Document composition rules

8. **Constraints**:
   - Add meaningful constraints
   - Validate constraints
   - Document constraint requirements

9. **Error Handling**:
   - Handle errors gracefully
   - Provide meaningful messages
   - Log errors appropriately

10. **Testing**:
    - Test service registration
    - Test service resolution
    - Test service lifecycle
    - Test service events
    - Test service constraints

## Examples

See the [examples](examples/) directory for complete examples of:

1. Basic service registration
2. Service configuration
3. Service lifecycle
4. Service events
5. Service versioning
6. Service composition
7. Service constraints
8. Error handling 