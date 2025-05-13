# Uno Snapshot Management System – Issues and Review (2025-05-13)

## General Principles & Uno Compliance

- [ ] **Type Hint Consistency:**  
  Sweep for legacy typing (`Any`, `Dict`, etc.) and ensure all type hints use modern Python 3.13+ idioms (`dict[str, X]`, `X | None`).
  - Some files use legacy type hints and untyped attributes.

- [ ] **Protocol Usage:**  
  Protocols for snapshots, stores, and strategies are present and use structural typing.
  - Confirm all implementations are checked against their protocols (not inherited).
  - Ensure protocol/interface names end with `Protocol`; concrete classes do not.

- [ ] **Error Handling:**  
  Audit for explicit error handling and custom error types (e.g., for missing snapshots, connection errors, etc.).
  - Avoid generic exceptions; use UnoError subclasses where appropriate.

## Implementation & Structure

- [ ] **Async/Sync Consistency:**  
  All store operations are async, which is good. Confirm all APIs and implementations maintain async consistency.
  - Consider sync adapters for test or legacy code if needed.

- [ ] **In-Memory Implementation:**  
  `InMemorySnapshotStore` uses a class-level dictionary for storage.
  - Ensure thread safety if used in concurrent scenarios (currently uses a plain dict without locks).
  - Confirm logger usage is robust and context-rich.

- [ ] **Postgres Implementation:**  
  `PostgresSnapshotStore` uses asyncpg and manages schema creation and snapshot persistence.
  - Confirm error handling for DB operations is robust (e.g., connection failures, serialization errors).
  - Ensure that schema migrations and upgrades are documented and tested.

- [ ] **Snapshot Strategies:**  
  Protocols for event count and time-based strategies exist.
  - Ensure all strategies are implemented and tested for correctness and performance.

- [ ] **Extensibility:**  
  Document how to add new snapshot types, stores, or strategies for contributors.
  - Ensure the interface for adding new persistent backends is clear and idiomatic.

## Documentation, Testability, and Maintainability

- [ ] **Internal Documentation:**  
  Most classes and methods have docstrings, but review for completeness and clarity, especially for maintainers.
  - Add/expand documentation for contributors.

- [ ] **Test Coverage:**  
  No evidence of comprehensive unit tests for:
  - Protocol/store compliance
  - Async store operations
  - Error handling (missing snapshot, DB errors, etc.)
  - Snapshot strategies and edge cases
  - Add/expand tests for these scenarios.

- [ ] **Examples:**  
  Ensure all major patterns (snapshot definition, store usage, error handling, strategies) are covered in `examples.py` or equivalent.

- [ ] **Dead Code:**  
  Remove any dead code, stubs, or unused helpers.

## Minor/Other Issues

- [ ] **Circular Imports:**  
  Use `TYPE_CHECKING` guards, but audit for possible circular import issues, especially between protocols, stores, and strategies.

---

**Next Steps:**

- Sweep for type hint modernization and protocol compliance.
- Ensure async consistency and robust error handling.
- Expand documentation and test coverage.
- Audit for circular imports, dead code, and maintainability.
