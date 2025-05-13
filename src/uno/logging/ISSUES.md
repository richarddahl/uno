# Uno Logging System – Issues and Review (2025-05-13)

## General Principles & Uno Compliance

- [ ] **Type Hint Consistency:**  
  Sweep for legacy typing (`Optional`, `Union`, etc.) and ensure all type hints use modern Python 3.13+ idioms (`X | None`, `X | Y`).
  - Some classes (e.g., `LoggingSettings`) use `Optional[str]` instead of `str | None`.

- [ ] **Protocol Usage:**  
  Protocols are correctly used for structural subtyping (e.g., `LoggerProtocol`, `LoggerFactoryProtocol`).  
  Ensure no classes inherit from Protocols directly (should only implement their interface).

- [ ] **Dependency Injection:**  
  The logger factory (`LoggerFactory`) is tightly coupled to the DI container.  
  Ensure the DI pattern is idiomatic Uno and documented for contributors.

## Logging Implementation & Structure

- [ ] **Logger Configuration:**  
  `LoggingSettings` class loads from environment variables, but lacks Pydantic v2 validation or config model.  
  Consider using Pydantic v2 for settings validation and environment parsing.

- [ ] **Structured Logging:**  
  `StructuredFormatter` and `UnoLogger` support structured/contextual logging.  
  Ensure all context propagation, serialization, and async context management are tested, especially with edge cases.

- [ ] **Logger Factory:**  
  `LoggerFactory` and `register_logger_factory` are present for DI, but their usage and lifecycle are not fully documented.  
  Ensure logger lifecycle, resource cleanup, and scope management are robust and covered by tests.

## Documentation, Testability, and Maintainability

- [ ] **Internal Documentation:**  
  Some classes and methods lack docstrings or usage notes, especially in `factory.py` and `scope.py`.  
  Add/expand documentation for maintainers and contributors.

- [ ] **Test Coverage:**  
  No evidence of comprehensive unit tests for:
  - Logger configuration via settings and environment
  - Structured/contextual logging output
  - Logger context propagation (sync/async)
  - Logger factory integration with DI
  Add/expand tests for these scenarios.

- [ ] **Examples:**  
  Ensure all major logging patterns (structured logging, context management, DI integration) are covered in `examples.py` or equivalent.

- [ ] **Dead Code:**  
  Remove any dead code, stubs, or unused helpers.

## Minor/Other Issues

- [ ] **Circular Imports:**  
  Use `TYPE_CHECKING` guards, but audit for possible circular import issues, especially between logger, protocols, and factory modules.

- [ ] **Extensibility:**  
  Document how to add new loggers, protocols, or context managers for contributors.

---

**Next Steps:**

- Sweep for type hint modernization and enum usage.
- Consider Pydantic v2 for settings/config.
- Expand documentation and test coverage.
- Audit for circular imports, dead code, and maintainability.
