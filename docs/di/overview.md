# Dependency Injection System Overview

## Introduction

The Uno framework's dependency injection (DI) system provides a robust mechanism for managing service dependencies in your application. It implements the Inversion of Control (IoC) principle, where components receive their dependencies rather than creating them directly. This approach leads to more modular, testable, and maintainable code.

## Key Features

- **Hierarchical Container**: Support for parent-child container relationships
- **Service Scopes**: Three levels of service lifetime management (Singleton, Scoped, Transient)
- **Automatic Dependency Resolution**: Automatically resolves constructor dependencies
- **Protocol-Based Injection**: Use Protocol classes to define service interfaces
- **Lifecycle Management**: Proper initialization and disposal of resources
- **Async Support**: First-class support for asynchronous services and scopes

## Architecture

The DI system consists of several key components:

1. **ServiceCollection**: Used to configure service registrations before building the container
2. **ServiceResolver**: Core resolver that manages service instances and resolves dependencies
3. **ServiceContainer**: Singleton access point to the service resolver
4. **ServiceProvider**: High-level API that manages service initialization and shutdown
5. **Protocol Interfaces**: Defines contracts for services to implement

## Core Concepts

### Service Scopes

The DI system supports three service lifetime scopes:

- **Singleton**: One instance per container, lives for the entire application lifetime
- **Scoped**: One instance per scope (e.g., per request), disposed when the scope ends
- **Transient**: New instance created each time the service is requested

### Service Registration

Services are registered with the container using a fluent API:

```python
services = ServiceCollection()
services.add_singleton(ServiceA)
services.add_scoped(ServiceB)
services.add_transient(ServiceC)
```

### Service Resolution

Services can be resolved from the container:

```python
# Direct resolution
service_a = get_service(ServiceA)

# Using scopes
with create_scope() as scope:
    service_b = scope.resolve(ServiceB)
```

### Protocol-Based Injection

The system uses Protocol classes from the `typing` module to define service interfaces:

```python
class MyServiceProtocol(Protocol):
    def perform_action(self) -> None: ...

# Implementation
class MyService:
    def perform_action(self) -> None:
        # Implementation here
        pass
```

## Getting Started

See the following documentation for more details:

- [Core Components](components.md) - Detailed information about each component
- [Usage Patterns](usage_patterns.md) - Common patterns and best practices
- [Examples](examples.md) - Practical examples of using the DI system