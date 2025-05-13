# Uno Projections System – Issues and Review (2025-05-13)

## General Principles & Uno Compliance

- [ ] **Type Hint Consistency:**  
  Sweep for legacy typing (`Dict`, `Any`, etc.) and ensure all type hints use modern Python 3.13+ idioms (`dict[str, T]`, `T | None`).
  - Some files (e.g., `memory.py`) use legacy type hints.

- [ ] **Protocol/ABC Usage:**  
  `Projection` uses `ABC` and `abstractmethod`, while `ProjectionStore` uses `Protocol`.
  - Confirm that all implementations use structural subtyping (not inheritance from Protocol).
  - Ensure naming is consistent: protocols/interfaces end with `Protocol`, concrete classes do not.

- [ ] **Error Handling:**  
  Custom errors (`ProjectionError`, `ProjectionStoreError`, `ProjectionNotFoundError`) are defined and inherit from `UnoError`.
  - Ensure all error raising and handling is explicit and uses these types, not generic exceptions.

## Implementation & Structure

- [ ] **Async/Sync Consistency:**  
  All store methods are async, which is good. Confirm all projections and stores maintain async consistency.
  - Consider providing sync adapters if needed for legacy or test code.

- [ ] **In-Memory Implementation:**  
  `InMemoryProjectionStore` is a generic, async, in-memory store.
  - Ensure thread safety if used in concurrent scenarios (currently uses a plain dict without locks).

- [ ] **Extensibility:**  
  Document how to add new projection types, stores, or error types for contributors.
  - Ensure the interface for adding new persistent backends is clear and idiomatic.

## Documentation, Testability, and Maintainability

- [ ] **Internal Documentation:**  
  Most classes and methods have docstrings, but review for completeness and clarity, especially for maintainers.
  - Add/expand documentation for contributors.

- [ ] **Test Coverage:**  
  No evidence of comprehensive unit tests for:
  - Projection protocol/store compliance
  - Async store operations
  - Error handling (store errors, not found, etc.)
  - Add/expand tests for these scenarios.

- [ ] **Examples:**  
  Ensure all major patterns (projection definition, store usage, error handling) are covered in `examples.py` or equivalent.

- [ ] **Dead Code:**  
  Remove any dead code, stubs, or unused helpers.

## Minor/Other Issues

- [ ] **Circular Imports:**  
  Use `TYPE_CHECKING` guards, but audit for possible circular import issues, especially between protocols, stores, and errors.

---

**Next Steps:**

- Sweep for type hint modernization and protocol compliance.
- Ensure async consistency and robust error handling.
- Expand documentation and test coverage.
- Audit for circular imports, dead code, and maintainability.
