# Service Lifecycle Management

Uno DI provides a robust service lifecycle management system that allows you to control the initialization and disposal of services throughout their lifetime. This is particularly useful for services that need to:

- Perform setup tasks when created
- Clean up resources when disposed
- Handle startup and shutdown hooks
- Manage service dependencies

## Service Lifecycle Protocol

To implement service lifecycle hooks, your service class should implement the `ServiceLifecycle` protocol:

```python
from uno.core.di import ServiceLifecycle

class MyService(ServiceLifecycle):
    async def initialize(self) -> None:
        """Called when the service is first created."""
        # Perform initialization tasks
        pass
    
    async def dispose(self) -> None:
        """Called when the service is being disposed."""
        # Clean up resources
        pass
```

## Service Initialization

Service initialization happens in two ways:

1. **Automatic Initialization**
   - Services are automatically initialized when first requested
   - Singleton services are initialized once at startup
   - Scoped services are initialized per scope
   - Transient services are initialized each time they're requested

2. **Explicit Initialization**
   - You can explicitly initialize services using `initialize_services()`
   - This is particularly useful for:
     - Early error detection
     - Performance optimization
     - Resource pre-allocation

```python
# Explicit initialization
provider.initialize_services()
```

## Service Disposal

Services are disposed in a controlled manner:

1. **Automatic Disposal**
   - Singleton services are disposed when the application shuts down
   - Scoped services are disposed when their scope ends
   - Transient services are disposed after each use

2. **Explicit Disposal**
   - You can explicitly dispose services using `shutdown_services()`
   - This is useful for:
     - Resource cleanup
     - Graceful shutdown
     - Testing cleanup

```python
# Explicit disposal
provider.shutdown_services()
```

## Service Scopes

Uno DI supports three service scopes:

1. **Singleton**
   - One instance per application
   - Initialized once at startup
   - Disposed when application shuts down

2. **Scoped**
   - One instance per scope
   - Initialized when scope begins
   - Disposed when scope ends

3. **Transient**
   - New instance each time requested
   - Initialized on each request
   - Disposed after each use

## Best Practices

1. **Resource Management**
   - Always implement proper disposal for services with resources
   - Use `async with` blocks for scoped resources
   - Implement proper error handling in lifecycle methods

2. **Initialization Order**
   - Ensure services are registered before their dependencies
   - Use service scopes appropriately
   - Consider pre-warming for critical services

3. **Error Handling**
   - Implement proper error handling in lifecycle methods
   - Log initialization errors
   - Consider failing fast for critical services

4. **Testing**
   - Test service initialization and disposal
   - Verify resource cleanup
   - Test service dependencies

## Advanced Usage

### Custom Lifecycle Management

You can implement custom lifecycle management by:

1. Extending the `ServiceLifecycle` protocol
2. Implementing custom initialization logic
3. Adding custom lifecycle hooks

```python
from uno.core.di import ServiceLifecycle

class CustomServiceLifecycle(ServiceLifecycle):
    async def initialize(self) -> None:
        await super().initialize()
        # Custom initialization
        pass
    
    async def dispose(self) -> None:
        # Custom disposal
        await super().dispose()
```

### Service Dependencies

Uno DI automatically handles service dependencies based on type hints:

```python
class MyService:
    def __init__(
        self,
        db: DatabaseProviderProtocol,
        config: ConfigProtocol
    ):
        self.db = db
        self.config = config
```

## Monitoring and Debugging

Uno DI provides built-in monitoring for service lifecycle events:

- Service initialization
- Service disposal
- Dependency resolution
- Error tracking

This information can be invaluable for:

- Debugging initialization issues
- Tracing service dependencies
- Monitoring resource usage
- Profiling startup performance

## Conclusion

Service lifecycle management is a crucial aspect of Uno's dependency injection system. By properly implementing and managing service lifecycles, you can create more reliable, maintainable, and performant applications.
