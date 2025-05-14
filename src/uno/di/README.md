# Uno Dependency Injection (DI) System

Uno's DI system provides a modern, type-safe, and testable approach to dependency injection for scalable Python applications. It is designed to be:

- **Extensible**: Easily register, resolve, and manage services with custom lifetimes
- **Testable**: Supports test doubles, fixtures, and overrides
- **Production-ready**: Robust error handling, async/sync support, and full traceability
- **Modern**: Uses Python 3.13, Pydantic v2, and idiomatic type hints

## Features
- Service registration by interface/type, factory, or async factory
- Three lifetimes: `singleton`, `scoped`, `transient`
- Scoped and nested resolution contexts
- Async and sync resolution APIs
- Circular dependency detection
- Rich error context and diagnostics
- Protocol-driven, type-safe API
- Integration with Uno's DI, config, logging, and error systems

## Quick Example
```python
from uno.di import Container, Lifetime

# Register a singleton service
container = Container()
container.register(IFoo, FooImpl, lifetime=Lifetime.singleton)

# Register a transient service with a factory
container.register(IBar, lambda c: BarImpl(), lifetime=Lifetime.transient)

# Resolve a service
foo = container.resolve(IFoo)

# Use async resolution (if needed)
bar = await container.resolve_async(IBar)
```

## Service Lifetimes
- **Singleton**: One instance per container
- **Scoped**: One instance per scope (useful for web requests, jobs, etc.)
- **Transient**: New instance every time

## Error Handling
All DI errors are subclasses of `DIError` and provide detailed context. See `src/uno/di/errors.py` for details.

## Advanced Usage
- Use `container.create_scope()` for isolated contexts
- Register async factories for async dependencies
- Integrate with Uno's config and logging via DI

## Further Reading
- [User Guide](../../../docs/di/user_guide.md)
- [Developer Guide](../../../docs/di/developer_guide.md)
- [API Reference](../../../docs/di/api_reference.md)

---
Uno DI is built for modern, maintainable, and scalable Python applications. See the full documentation in `docs/di/` for details and advanced usage.
