# Uno Utilities – Issues and Review (2025-05-13)

## General Principles & Uno Compliance

- [ ] **Type Hint Consistency:**  
  Sweep for legacy typing (`Any`, etc.) and ensure all type hints use modern Python 3.13+ idioms (`dict[str, X]`, `X | None`).
  - Some function signatures and arguments use `Any` or lack explicit type hints.

- [ ] **Protocol Usage:**  
  `HashServiceProtocol` is defined and used correctly for structural typing.
  - Ensure all implementations are checked for compliance, not inheritance.

- [ ] **Extensibility:**  
  Document how to add new utility protocols or implementations for contributors.
  - Ensure all utilities are discoverable and composable.

## Implementation & Structure

- [ ] **DefaultHashService:**  
  Inherits from `BaseModel` but does not use Pydantic features; consider removing inheritance if not needed.
  - Constructor logic may bypass Pydantic validation.
  - Ensure error handling for unsupported algorithms is robust and uses UnoError subclasses where appropriate.
  - Confirm compliance with `HashServiceProtocol`.

- [ ] **HTTP Utilities:**  
  `to_http_error_response` assumes all error fields are present and of correct type; add type safety and error handling.
  - Ensure all sensitive information is sanitized; expand `sanitize_sensitive_info` to cover more cases if needed.

- [ ] **Security Utilities:**  
  `sanitize_sensitive_info` only removes the `"sensitive"` key; consider making this extensible/configurable for other sensitive fields.

## Documentation, Testability, and Maintainability

- [ ] **Internal Documentation:**  
  Most functions have docstrings, but review for completeness and clarity, especially for maintainers.
  - Add/expand documentation for contributors and implementers.

- [ ] **Test Coverage:**  
  No evidence of comprehensive unit tests for:
  - Hash service protocol and default implementation
  - HTTP error response generation and sanitization
  - Security utilities
  - Add/expand tests for these scenarios.

- [ ] **Examples:**  
  Ensure all major patterns (hashing, HTTP error handling, security) are covered in `examples.py` or equivalent.

- [ ] **Dead Code:**  
  Remove any dead code, stubs, or unused helpers.

## Minor/Other Issues

- [ ] **Circular Imports:**  
  Use `TYPE_CHECKING` guards, but audit for possible circular import issues, especially between HTTP and security utilities.

---

**Next Steps:**
- Sweep for type hint modernization and protocol compliance.
- Ensure robust error handling and extensibility.
- Expand documentation and test coverage.
- Audit for circular imports, dead code, and maintainability.
