# Uno DI System – Issues and Review

This document lists all issues and concerns identified in the current implementation of the Uno Dependency Injection (DI) system as of 2025-05-13.

## General Principles & Compliance

- [ ] **Type Hint Consistency:** Some type hints use `Optional[X]` or `Union[X, Y]` patterns. Per Uno rules, use `X | None` and `X | Y` (PEP 604 style) everywhere. Sweep for legacy typing usage.
- [ ] **Modern Python Compliance:** Ensure all type hints and syntax are Python 3.13+ idiomatic. Avoid deprecated typing constructs.
- [ ] **No Built-in Shadowing:** Confirm that no class/function/constant names shadow Python built-ins or imported package names.
- [ ] **No Python Keywords as Identifiers:** Audit for any accidental use of Python keywords as names.

## Dependency Injection Patterns

- [ ] **Protocol Usage:** Protocols are correctly used for structural subtyping, not inheritance. However, ensure all Protocol imports are in `if TYPE_CHECKING:` blocks to avoid runtime import overhead (see Uno rules/memories).
- [ ] **DI API Consistency:** Some registration/resolution APIs are both sync and async. Convert them all to async.

  **Migration Checklist:**
  - [x] Identify all sync DI registration and resolution methods (e.g., `register_singleton`, `register_scoped`, `resolve`, etc.)
    - [x] `Container.get_registration_keys(self) -> list[str]`
    - [x] `ContainerProtocol.get_registration_keys(self) -> list[str]` (protocol)
    - [x] `_Scope.__setitem__(self, interface: type[T], service: T) -> None`
    - [x] `_Scope.get_service_keys(self) -> list[str]`
  - [x] Refactor all DI error classes and usages to be async-only (e.g., DICircularDependencyError, DIServiceCreationError, ContainerError, and tests now use async_init)
  - [x] Update all internal usages and tests to use `await ...async_init(...)` for DI error creation and container state capture
  - [x] Refactor remaining registration/resolution methods to be `async def` only; remove or deprecate sync versions
  - [x] Update all internal usages to use `await` for DI operations
  - [x] Update all tests to use async DI APIs (with `pytest.mark.asyncio` as needed)
  - [ ] Update documentation to reflect async-only DI API
  - [ ] Add migration notes for users upgrading from previous versions

- [ ] **Service Registration API:** The registration API in `registration.py` is not fully type safe (e.g., use of `Any` in places). Consider stricter type bounds for all generics.
- [ ] **ConfigProvider Registration:** The `register_secure_config` function in `config.py` uses `Any` for the container type. This should be properly typed as `Container` or `ContainerProtocol` for type safety.

## Error Handling

- [ ] **Error Context Propagation:** Error classes are generally robust, but ensure all error contexts propagate full dependency chains, constructor signatures, and relevant metadata for debugging (especially in `DIServiceCreationError`, `DICircularDependencyError`).
- [ ] **Redundant Error Classes:** There is duplication between base and enhanced error types (e.g., `ServiceNotRegisteredError` vs `DIServiceNotFoundError`). Consolidate error classes to avoid confusion and ensure consistency.

## Logging & Observability

- [ ] **Logger Injection:** Logger injection is attempted in several places (e.g., `ConfigProvider`, `Container`). Ensure logger factories are always resolved via DI and never instantiated directly except as a fallback.
- [ ] **Logger Scope Handling:** The logger scope logic in `Container.create_scope` is fragile (uses string names, checks for attributes at runtime). Consider a more robust interface for logger-scope integration.

## Extensibility & Maintainability

- [ ] **Service Lifetime Management:** The `_Scope` class in `resolution.py` uses internal logic for singleton/scoped/transient. Consider exposing lifetime management in a more extensible way (e.g., via strategy objects or explicit lifetime policies).
- [ ] **Test Coverage:** There is no evidence of comprehensive unit tests for error paths, lifetime edge cases, or circular dependency handling. Add/expand tests for these scenarios.
- [ ] **Documentation:** Public APIs are well-documented, but internal/private APIs (e.g., `_DisposalManager`, `_Scope`) lack docstrings and usage notes. Add internal documentation for maintainers.

## Minor/Other Issues

- [ ] **Circular Imports:** Some modules use `TYPE_CHECKING` guards, but audit for any possible circular import issues, especially in error handling and protocols.
- [ ] **Redundant Async/Synchronous APIs:** Review for unnecessary duplication between sync and async API variants.
- [ ] **Type Aliases:** `types.py` is minimal; confirm all type aliases are defined in the most appropriate module to avoid circular dependencies (see Uno memories).

---

**Next Steps:**

- Sweep all DI code for modern type hints and Uno idioms
- Improve test coverage for error paths, lifetimes, and circular dependencies
- Expand internal documentation and clarify error class usage
- Refactor logger scope and config provider registration for robustness and type safety
- Audit for circular imports and redundant APIs

*Generated by automated review on 2025-05-13.*
