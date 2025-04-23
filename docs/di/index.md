# Dependency Injection

Uno's Dependency Injection (DI) system is a powerful tool for managing service dependencies in your application. It provides a robust, type-safe, and performant way to handle service registration, resolution, and lifecycle management.

## Key Concepts

### Service Lifetimes
Uno DI supports three main service lifetimes:

- **Singleton**: A single instance is created and shared throughout the application
- **Scoped**: A new instance is created per scope (typically a request or operation)
- **Transient**: A new instance is created each time the service is requested

### Service Registration
Services can be registered in several ways:

```python
# Basic registration
collection.add_singleton(IMyService, MyServiceImpl)
collection.add_scoped(IAnotherService, AnotherServiceImpl)
collection.add_transient(ITransientService, TransientServiceImpl)

# Instance registration
collection.add_instance(IMyService, MyServiceImpl())
```

## Auto-registration

Uno DI supports automatic service registration, which can simplify your dependency management:

```python
# Enable auto-registration
collection.enable_auto_registration(packages=["my.package"])

# Or set the environment variable
export UNO_DI_AUTO_REGISTER=true
```

## Pre-warming

Pre-warming is a powerful feature that allows you to:

1. Initialize services early during startup
2. Detect configuration or dependency issues early
3. Improve startup performance by resolving dependencies ahead of time

```python
# Pre-warm services
collection.initialize_services()
```

## Testing

Uno DI includes built-in support for testing your services:

```python
from uno.core.di.test_helpers import TestServiceProvider

def test_my_service():
    # Create a test service provider
    provider = TestServiceProvider()
    
    # Register test services
    provider.register_singleton(MyServiceImpl)
    
    # Get and test the service
    service = provider.get_service(MyServiceImpl)
    assert service is not None
```

## Advanced Topics

- [Service Lifecycle Hooks](service-lifecycle.md)
- [Service Factories](service-factories.md)
- [Custom Service Resolvers](custom-resolvers.md)
- [Performance Optimization](performance.md)
