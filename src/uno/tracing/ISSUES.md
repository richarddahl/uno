# Uno Tracing System – Issues and Review (2025-05-13)

## General Principles & Uno Compliance

- [ ] **Type Hint Consistency:**  
  Sweep for legacy typing (`Any`, etc.) and ensure all type hints use modern Python 3.13+ idioms (`dict[str, X]`, `X | None`).
  - Some function signatures and variables use `Any` or lack explicit type hints.

- [ ] **Protocol/Interface Usage:**  
  No protocols or interfaces are defined for tracing context or span management.
  - Define and use Protocols for extensibility and backend support (e.g., OpenTelemetry, custom tracers).

- [ ] **Extensibility:**  
  Current implementation is minimal and in-memory only.
  - Document and implement how to add or swap tracing backends (e.g., OpenTelemetry, Jaeger, Zipkin).
  - Ensure clear separation between context management and backend reporting.

## Implementation & Structure

- [ ] **Distributed Context Management:**  
  Uses `contextvars` for trace and span IDs, which is correct for async compatibility.
  - Ensure context propagation works across async boundaries, threads, and process boundaries if needed.
  - Provide utilities for extracting/injecting context from/to HTTP headers (W3C Trace Context).

- [ ] **Trace/Span Utilities:**  
  `trace_span` utility is referenced but not shown—ensure it is implemented and supports context management, nesting, and error handling.
  - Provide context manager/decorator for tracing spans.

- [ ] **Error Handling:**  
  Integrate tracing with Uno error handling system (e.g., attach trace context to errors, logs).
  - Avoid generic exceptions; use UnoError subclasses where appropriate.

## Documentation, Testability, and Maintainability

- [ ] **Internal Documentation:**  
  Most functions have docstrings, but review for completeness and clarity, especially for maintainers.
  - Add/expand documentation for contributors and backend implementers.

- [ ] **Test Coverage:**  
  No evidence of comprehensive unit tests for:
  - Context propagation (sync/async)
  - Trace/span creation and nesting
  - Integration with error handling and logging
  - Backend integration (if any)
  - Add/expand tests for these scenarios.

- [ ] **Examples:**  
  Ensure all major patterns (context management, span usage, backend integration) are covered in `examples.py` or equivalent.

- [ ] **Dead Code:**  
  Remove any dead code, stubs, or unused helpers.

## Minor/Other Issues

- [ ] **Circular Imports:**  
  Use `TYPE_CHECKING` guards, but audit for possible circular import issues, especially if/when adding backends.

---

**Next Steps:**

- Sweep for type hint modernization and protocol/interface usage.
- Implement and document backend extensibility.
- Expand documentation and test coverage.
- Audit for circular imports, dead code, and maintainability.
