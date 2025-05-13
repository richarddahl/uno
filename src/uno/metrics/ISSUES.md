# Uno Metrics System – Issues and Review (2025-05-13)

## General Principles & Uno Compliance

- [ ] **Type Hint Consistency:**  
  Sweep for legacy typing (`Optional`, `Dict`, `List`, etc.) and ensure all type hints use modern Python 3.13+ idioms (`X | None`, `dict[str, Any]`, `list[X]`).
  - Some files (e.g., `implementations/memory.py`, `collector.py`, `backends/logging.py`) use legacy type hints.

- [ ] **Protocol Usage:**  
  Protocols are used for interface definitions (e.g., `MetricProtocol`, `CounterProtocol`, `TimerProtocol`).
  - Ensure no classes inherit from Protocols directly—only implement their interface.
  - Confirm all implementations are actually checked against their protocols.

- [ ] **Naming and Structure:**  
  Protocols should be defined in `protocols.py` or `backends/protocols.py` and have a `Protocol` suffix.
  - Concrete implementations should have clear, descriptive names and not use the `Protocol` suffix.

## Implementation & Structure

- [ ] **Async/Sync Consistency:**  
  Most metric collectors and stores are async, but confirm all APIs and implementations are consistently async or provide sync adapters where needed.
  - Ensure thread safety and context management are robust (e.g., use of `asyncio.Lock`).

- [ ] **Metrics Backends:**  
  Logging and Prometheus backends exist, but ensure all backends conform to the same protocol and are easily swappable.
  - Confirm error handling is robust in all reporters/exporters.

- [ ] **Metric Registry/Discovery:**  
  Ensure there is a clear registry or discovery mechanism for metrics and backends.
  - Document how to register and use custom metrics/backends.

## Documentation, Testability, and Maintainability

- [ ] **Internal Documentation:**  
  Many classes and methods lack docstrings or usage notes, especially in `implementations`, `collector.py`, and `registry.py`.
  - Add/expand documentation for maintainers and contributors.

- [ ] **Test Coverage:**  
  No evidence of comprehensive unit tests for:
    - Metric protocol compliance
    - Async metric collection/reporting
    - Backend integration (logging, Prometheus)
    - Error handling and edge cases
  - Add/expand tests for these scenarios.

- [ ] **Examples:**  
  Ensure all major metrics patterns (async collection, backend reporting, custom metric creation) are covered in `examples.py` or equivalent.

- [ ] **Dead Code:**  
  Remove any dead code, stubs, or unused helpers.

## Minor/Other Issues

- [ ] **Circular Imports:**  
  Use `TYPE_CHECKING` guards, but audit for possible circular import issues, especially between protocols, implementations, and backends.

- [ ] **Extensibility:**  
  Document how to add new metric types, protocols, or backends for contributors.

---

**Next Steps:**
- Sweep for type hint modernization and protocol compliance.
- Ensure async/sync consistency and robust context/thread safety.
- Expand documentation and test coverage.
- Audit for circular imports, dead code, and maintainability.
