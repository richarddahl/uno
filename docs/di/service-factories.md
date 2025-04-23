# Service Factories

Service factories in Uno DI provide a flexible way to create and manage service instances. They allow you to:

- Control service creation logic
- Implement custom initialization
- Manage service dependencies
- Handle complex service configurations

## Basic Service Factories

Uno DI provides a simple way to register service factories:

```python
from uno.core.di import ServiceCollection

def create_my_service() -> MyService:
    return MyService()

collection = ServiceCollection()
collection.add_singleton(MyService, create_my_service)
```

## Factory Protocol

For more complex scenarios, you can implement the `ServiceFactory` protocol:

```python
from uno.core.di import ServiceFactory

class MyServiceFactory(ServiceFactory[MyService]):
    def __call__(self, provider: ServiceProvider) -> MyService:
        # Access other services through the provider
        config = provider.get_service(ConfigProtocol)
        return MyService(config)
```

## Factory Methods

You can also use factory methods:

```python
class MyService:
    @classmethod
    def create(cls, config: ConfigProtocol) -> "MyService":
        return cls(config)

# Register with factory method
collection.add_singleton(MyService, MyService.create)
```

## Factory Functions

Use factory functions for complex initialization:

```python
def create_complex_service(
    provider: ServiceProvider,
    config_key: str = "default"
) -> ComplexService:
    config = provider.get_service(ConfigProtocol)
    db = provider.get_service(DatabaseProviderProtocol)
    return ComplexService(config, db)

# Register with factory function
collection.add_singleton(ComplexService, create_complex_service)
```

## Factory Parameters

You can pass parameters to factories:

```python
def create_configured_service(config_value: str) -> ConfiguredService:
    return ConfiguredService(config_value)

# Register with parameters
collection.add_singleton(
    ConfiguredService,
    create_configured_service,
    config_value="production"
)
```

## Factory Scopes

Factories work with all service scopes:

```python
# Singleton scope
collection.add_singleton(MyService, create_my_service)

# Scoped service
collection.add_scoped(MyService, create_my_service)

# Transient service
collection.add_transient(MyService, create_my_service)
```

## Best Practices

1. **Factory Design**
   - Keep factories focused and single-purpose
   - Use dependency injection for service dependencies
   - Implement proper error handling
   - Document factory requirements

2. **Service Initialization**
   - Perform initialization in factories
   - Handle resource allocation
   - Implement proper cleanup
   - Consider lazy initialization

3. **Dependency Management**
   - Use type hints for dependencies
   - Handle optional dependencies
   - Implement fallback logic
   - Consider service lifetimes

4. **Testing**
   - Test factory functions
   - Verify service creation
   - Test dependency resolution
   - Check error handling

## Advanced Usage

### Factory Composition

Combine multiple factories:

```python
def create_base_service() -> BaseService:
    return BaseService()

def create_extended_service(base: BaseService) -> ExtendedService:
    return ExtendedService(base)

# Register composed services
collection.add_singleton(BaseService, create_base_service)
collection.add_singleton(ExtendedService, create_extended_service)
```

### Factory Decorators

Use decorators to enhance factories:

```python
def with_logging(factory):
    def wrapper(*args, **kwargs):
        result = factory(*args, **kwargs)
        print(f"Created service: {type(result).__name__}")
        return result
    return wrapper

@with_logging
def create_logged_service() -> LoggedService:
    return LoggedService()
```

### Factory Inheritance

Create factory hierarchies:

```python
class BaseServiceFactory:
    def create(self) -> BaseService:
        return BaseService()

class ExtendedServiceFactory(BaseServiceFactory):
    def create(self) -> ExtendedService:
        base = super().create()
        return ExtendedService(base)
```

## Performance Considerations

1. **Factory Overhead**
   - Keep factory functions lightweight
   - Cache expensive computations
   - Consider lazy initialization

2. **Service Creation**
   - Optimize service initialization
   - Use appropriate service scopes
   - Consider pre-warming
   - Profile service creation

3. **Dependency Resolution**
   - Use efficient dependency injection
   - Cache resolved dependencies
   - Consider dependency order
   - Monitor resolution performance

## Error Handling

Implement proper error handling in factories:

```python
def create_service_with_error_handling() -> MyService:
    try:
        # Service creation logic
        return MyService()
    except Exception as e:
        # Handle initialization errors
        raise ServiceInitializationError(f"Failed to create service: {e}")
```

## Conclusion

Service factories are a powerful feature of Uno DI that provide flexibility and control over service creation. By properly implementing and using factories, you can create more maintainable, testable, and performant applications.
