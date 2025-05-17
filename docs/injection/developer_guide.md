# Uno DI Developer Guide

## Architecture

Uno DI is built around a protocol-driven, type-safe core. All interfaces are defined as Protocols for maximum flexibility and static analysis. The main entry point is the `Container` class, which manages service registration, resolution, and lifetime policies.

### Key Modules

- `container.py`: Core DI container implementation
- `protocols.py`: Protocols for container, scope, factories, and registration
- `registration.py`: Service registration objects
- `errors.py`: Rich error types with context propagation
- `lifetime_policies.py`: Lifetime management logic
- `resolution.py`: Resolution and scope internals

## Extending the DI System

- Implement custom lifetimes by adding to `lifetime_policies.py`
- Add custom error types by subclassing `DIError`
- Extend container behavior by subclassing `Container` (advanced)

## Testing with DI

- Use test scopes for isolation
- Register test doubles (Fake/Mock) using the container
- Override services in test setup/fixtures

## Integration

- Use Uno's config and logging systems via DI
- Register config providers and loggers as services
- Compose complex applications by wiring modules via DI

## Debugging & Diagnostics

- All errors propagate context (dependency chain, scope, etc.)
- Use error types to catch and diagnose issues
- Container and scope state can be inspected for debugging

## Conventions

- Use modern type hints (Python 3.13 idioms)
- Protocols for all interfaces
- Never inherit from Protocols, only implement their methods
- Avoid naming collisions with Python keywords or built-ins

## Reference

See [API Reference](api_reference.md) for full details on protocols, classes, and error types.
