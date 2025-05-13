# Uno Unit of Work System – Issues and Review (2025-05-13)

## General Principles & Uno Compliance

- [ ] **Type Hint Consistency:**  
  Sweep for legacy typing (`Any`, `Dict`, etc.) and ensure all type hints use modern Python 3.13+ idioms (`dict[str, X]`, `X | None`).
  - Some function signatures and attributes use legacy or missing type hints.

- [ ] **Protocol/ABC Usage:**  
  The `UnitOfWork` protocol is an ABC, not a structural Protocol. Consider using a Protocol for interface definition and ABC for base class only if default logic is provided.
  - Ensure all implementations are checked for compliance, not inheritance.

- [ ] **Error Handling:**  
  Custom errors (`UnitOfWorkError`, `UnitOfWorkCommitError`, `UnitOfWorkRollbackError`, `TransactionError`) are defined and inherit from `UnoError`.
  - Audit for direct `raise Exception` or similar anti-patterns in implementations.

## Implementation & Structure

- [ ] **Async/Sync Consistency:**  
  All UoW operations are async, which is good. Confirm all APIs and implementations maintain async consistency.
  - Consider sync adapters for test or legacy code if needed.

- [ ] **In-Memory Implementation:**  
  `InMemoryUnitOfWork` is suitable for testing but lacks persistence and may not cover all transactional edge cases.
  - Ensure robust state management and clear documentation of limitations.

- [ ] **Postgres Implementation:**  
  `PostgresUnitOfWork` uses SQLAlchemy async session/transaction and supports DI for logging.
  - Confirm error handling for DB operations is robust (e.g., commit/rollback failures).
  - Ensure transactional boundaries are correctly enforced and integrated with event store.
  - Audit logger usage for completeness and context.

- [ ] **Extensibility:**  
  Document how to add new UoW implementations or backends for contributors.
  - Ensure the interface for adding new persistent backends is clear and idiomatic.

## Documentation, Testability, and Maintainability

- [ ] **Internal Documentation:**  
  Most classes and methods have docstrings, but review for completeness and clarity, especially for maintainers.
  - Add/expand documentation for contributors and backend implementers.

- [ ] **Test Coverage:**  
  No evidence of comprehensive unit tests for:
  - Protocol/ABC compliance
  - Async UoW operations
  - Error handling (commit/rollback/transaction errors)
  - Integration with event sourcing and DDD patterns
  - Add/expand tests for these scenarios.

- [ ] **Examples:**  
  Ensure all major patterns (UoW definition, transactional boundaries, error handling, backend usage) are covered in `examples.py` or equivalent.

- [ ] **Dead Code:**  
  Remove any dead code, stubs, or unused helpers.

## Minor/Other Issues

- [ ] **Circular Imports:**  
  Use `TYPE_CHECKING` guards, but audit for possible circular import issues, especially between protocols, errors, and implementations.

---

**Next Steps:**
- Sweep for type hint modernization and protocol/ABC compliance.
- Ensure async consistency and robust error handling.
- Expand documentation and test coverage.
- Audit for circular imports, dead code, and maintainability.
