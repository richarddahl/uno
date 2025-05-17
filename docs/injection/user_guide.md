# Uno DI User Guide

## Overview

Uno's Dependency Injection (DI) system provides a robust, type-safe, and testable approach to managing dependencies in modern Python applications. It supports async and sync workflows, custom lifetimes, and is fully integrated with Uno's config, logging, and error systems.

## Motivation

- Decouple components for testability and maintainability
- Manage complex dependency graphs
- Enable easy overrides for testing and configuration

## Core Concepts

- **Container**: Central registry for services
- **Service Registration**: Binding an interface/type to an implementation or factory
- **Lifetimes**: `singleton`, `scoped`, `transient`
- **Scope**: Isolated resolution context (e.g., per-request)
- **Protocols**: All interfaces are defined as Protocols for type safety

## Getting Started

```python
from uno.di import Container, Lifetime

container = Container()
container.register(IMyService, MyServiceImpl, lifetime=Lifetime.singleton)
service = container.resolve(IMyService)
```

## Registering Services

- By type: `container.register(IFoo, FooImpl, lifetime=Lifetime.singleton)`
- By factory: `container.register(IBar, lambda c: BarImpl(), lifetime=Lifetime.transient)`
- By async factory: `container.register_async(IFoo, async_factory, lifetime=Lifetime.scoped)`

## Resolving Services

- Sync: `service = container.resolve(IMyService)`
- Async: `service = await container.resolve_async(IMyService)`

## Using Scopes

```python
scope = await container.create_scope()
scoped_service = await scope.resolve(IMyService)
await scope.dispose()
```

## Error Handling

All errors are subclasses of `DIError` and provide rich context. For example, `DIServiceNotFoundError`, `DuplicateRegistrationError`, and `DICircularDependencyError`.

## Best Practices

- Register interfaces, not concrete types
- Prefer factories for complex construction
- Use scopes for per-request or per-job isolation
- Integrate config/logging via DI

## See Also

- [API Reference](api_reference.md)
- [Developer Guide](developer_guide.md)
- [Examples](examples/)
