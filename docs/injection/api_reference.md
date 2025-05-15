# Uno DI API Reference

## Public API

### Container

- `Container`
  - `register(interface, implementation, lifetime)`
  - `register_async(interface, async_factory, lifetime)`
  - `resolve(interface)`
  - `resolve_async(interface)`
  - `create_scope()`
  - `dispose()`

### Protocols

- `ContainerProtocol`: Interface for DI containers
- `ScopeProtocol`: Interface for scopes
- `ServiceRegistrationProtocol`: Interface for service registrations
- `ServiceFactoryProtocol`: Type alias for sync factories
- `AsyncServiceFactoryProtocol`: Type alias for async factories
- `Lifetime`: Literal type for lifetimes (`"singleton"`, `"scoped"`, `"transient"`)

### Errors

- `DIError`: Base error
- `DIServiceCreationError`: Service creation failure
- `DIServiceNotFoundError`: Service not found
- `DuplicateRegistrationError`: Duplicate registration
- `DICircularDependencyError`: Circular dependency detected
- `ScopeError`: Scope/lifetime violation
- `ContainerDisposedError`: Disposed container
- `DIScopeDisposedError`: Disposed scope
- `TypeMismatchError`: Implementation does not match interface
- `SyncInAsyncContextError`: Sync API called in async context

### Service Registration

- `ServiceRegistration`
  - `interface`
  - `implementation`
  - `lifetime`
  - `is_factory`
  - `is_async_factory`

## Type Hints

- All public APIs use modern Python 3.13 type hints
- Prefer `X | Y` over `Union[X, Y]`, `X | None` over `Optional[X]`, etc.

## See Also

- [User Guide](user_guide.md)
- [Developer Guide](developer_guide.md)
- [Examples](examples/)
