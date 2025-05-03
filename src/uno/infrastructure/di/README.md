# Uno Dependency Injection

Uno's Dependency Injection (DI) system provides a robust, type-safe, and performant way to manage service dependencies in your application. It supports singleton, scoped, and transient lifetimes, automatic service discovery, and pre-warming for optimized startup performance.

## Key Features

- **Type-safe Service Registration**: Strong type hints and validation
- **Automatic Service Discovery**: Seamless registration of services
- **Service Lifetimes**: Singleton, Scoped, and Transient
- **Pre-warming**: Optimized startup time and early error detection
- **Testing Support**: Built-in test helpers
- **Service Lifecycle Hooks**: Initialize and shutdown services

## Getting Started

```python
from uno.core.di import ServiceCollection, ServiceScope

# Create a service collection
collection = ServiceCollection()

# Register services
collection.add_singleton(MyServiceImpl)
collection.add_scoped(AnotherServiceImpl)

# Build and use the service provider
provider = collection.build_provider()
service = provider.get_service(MyServiceImpl)
```

## Documentation

For comprehensive documentation, see:
- [Getting Started](https://uno-framework.readthedocs.io/en/latest/di/getting-started.html)
- [Service Lifetimes](https://uno-framework.readthedocs.io/en/latest/di/service-lifetimes.html)
- [Auto-registration](https://uno-framework.readthedocs.io/en/latest/di/auto-registration.html)
- [Testing](https://uno-framework.readthedocs.io/en/latest/di/testing.html)
- [Advanced Topics](https://uno-framework.readthedocs.io/en/latest/di/advanced.html)
