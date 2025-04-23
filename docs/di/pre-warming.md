# Pre-warming in Uno DI

Pre-warming is a powerful feature in Uno DI that allows you to initialize services early during application startup. This feature provides several important benefits:

## Benefits of Pre-warming

### Early Error Detection

One of the most significant benefits of pre-warming is that it allows you to detect configuration and dependency issues early in the application lifecycle. Instead of encountering errors when a service is first requested, pre-warming ensures that all services are:

- Successfully instantiated
- Have their dependencies resolved
- Have their initialization hooks called

This means that if there are any issues with your service configuration or dependencies, you'll know about them immediately during startup rather than at runtime.

### Improved Startup Performance

Pre-warming can improve startup performance by:

1. Resolving dependencies ahead of time
2. Initializing services in parallel
3. Caching resolved instances (for singleton services)

This can be particularly beneficial in applications with many services or complex dependency chains.

### Consistent State

Pre-warming ensures that all services are in a consistent initialized state before the application starts handling requests. This is especially important for:

- Services that need to perform initialization tasks
- Services that depend on other services being initialized
- Services that need to establish connections or resources

## How to Use Pre-warming

Pre-warming is simple to use. After registering your services, you can call `initialize_services()`:

```python
# Create and configure service collection
collection = ServiceCollection()
collection.add_singleton(IMyService, MyServiceImpl)
# ... other service registrations ...

# Build service provider
provider = collection.build_provider()

# Pre-warm services
provider.initialize_services()
```

## Best Practices

1. **Use Pre-warming in Production**
   - Always pre-warm services in production to catch issues early
   - This is especially important in distributed systems

2. **Selective Pre-warming**
   - You can selectively pre-warm services by name or type
   - This is useful for large applications with many services

3. **Error Handling**
   - Implement proper error handling during pre-warming
   - Log initialization errors for debugging
   - Consider failing fast if critical services fail to initialize

4. **Performance Considerations**
   - Be mindful of the overhead of pre-warming
   - Consider lazy initialization for expensive services
   - Use service scopes appropriately to control initialization

## Advanced Usage

### Custom Initialization

You can implement custom initialization logic in your services by implementing the `ServiceLifecycle` protocol:

```python
from uno.core.di import ServiceLifecycle

class MyService(ServiceLifecycle):
    async def initialize(self, provider: ServiceProvider) -> None:
        # Perform initialization tasks
        pass
    
    async def shutdown(self) -> None:
        # Clean up resources
        pass
```

### Parallel Initialization

Uno DI can initialize services in parallel when possible, which can significantly improve startup performance. The system automatically handles parallel initialization while respecting dependency order.

### Service Validation

Pre-warming includes automatic service validation to ensure:

- All required dependencies are resolved
- Service implementations match their interfaces
- Circular dependencies are detected
- Service lifetimes are compatible

## Monitoring and Debugging

When using pre-warming, you can monitor the initialization process through:

- Logging (enabled by default)
- Performance metrics
- Dependency resolution graphs
- Error tracking

This information can be invaluable for debugging initialization issues and optimizing startup performance.

## Conclusion

Pre-warming is a powerful feature that enhances the reliability and performance of Uno applications. By catching issues early and improving startup performance, it provides significant benefits with minimal overhead. When used correctly, it can make your application more robust and easier to maintain.
