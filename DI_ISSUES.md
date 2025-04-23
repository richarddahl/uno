# Uno DI System: Issues & Recommendations (2025-04-22)

This document provides a thorough review of the Uno Dependency Injection (DI) system in `uno.core.di`, highlighting issues, limitations, and recommendations to ensure a robust, modern, and developer-friendly DI framework for DDD/event-driven applications.

---

## 1. **API Clarity & Usability**

### Issues
- **Public vs. Internal API**: Internal classes (e.g., `_ServiceResolver`, `ServiceRegistration`) are exposed in module imports and not clearly separated from the public API.
- **Advanced Usage Leakage**: Extensibility hooks and advanced APIs are not clearly marked or separated, risking accidental use by typical users.

### Recommendations
- Move all internal/advanced classes to a dedicated private submodule or prefix with double-underscore (`__`).
- Clearly document public APIs in `README.md` and module docstrings.
- Provide a minimal, clean import surface for end-users (e.g., `ServiceProvider`, `ServiceCollection`, `ServiceScope`).

---

## 2. **Error Handling & Result Pattern**

### Issues
- **Inconsistent Exception Usage**: Most DI operations use the `Success`/`Failure` monad with specific error types, but some utility/validation code (e.g., `discovery.py:validate_service_discovery`) still raises exceptions directly (`RuntimeError`).
- **Legacy Exception Handling**: Some legacy code or comments may reference exceptions or raise them in non-core paths.

### Recommendations
- Refactor all DI-related utilities (including discovery/validation) to consistently return `Success`/`Failure` results or raise only for truly unrecoverable errors (not for validation failures).
- Audit all exception-raising code and document when raising is appropriate vs. returning a result.

---

## 3. **Testing & Developer Experience**

### Issues
- **Test Helper Coverage**: While core tests are robust, test helpers (`test_helpers.py`) could provide more utilities for mocking, stubbing, and overriding services in tests.
- **Best Practices**: Lack of documentation/examples for DI in unit/integration tests.

### Recommendations
- Expand `test_helpers.py` with utilities for common test patterns (mocking, override, teardown).
- Add documentation and code examples for testing with DI.

---

## 4. **Service Discovery & Decorators**

### Issues
- **Limited Discovery Patterns**: `@framework_service` only marks classes; property/parameter injection and auto-registration patterns are not yet supported.
- **Manual Registration Still Required**: Developers must remember to decorate and/or explicitly register services.
- **Discovery Strictness**: `validate_service_discovery` can raise at runtime if strict, which may surprise users.

### Recommendations
- Enhance `@framework_service` and discovery utilities to support property/parameter injection, auto-registration, and more expressive patterns.
- Consider offering opt-in auto-registration for all discovered services, with clear override mechanisms.
- Make discovery validation failures return structured results, not just raise.

---

## 5. **Configuration & Conditional Registration**

### Issues
- **Limited Environment Support**: No built-in support for environment-based or conditional registration (e.g., different services for dev/prod).
- **Manual Validation**: Service configuration validation hooks are present but not widely documented or leveraged.

### Recommendations
- Add first-class support for environment-based/conditional registration (e.g., via config or decorator arguments).
- Document and encourage use of validation hooks for robust configuration.

---

## 6. **Performance & Caching**

### Issues
- **Resolution Path Caching**: No explicit caching of dependency resolution paths or lazy loading for performance-critical paths.
- **Prewarming**: Prewarming is available but not documented as a best practice.

### Recommendations
- Implement resolution path caching and lazy loading for singleton/scoped services.
- Document prewarming and its benefits for startup time and error detection.

---

## 7. **Advanced Patterns & Extensibility**

### Issues
- **No Support for Named/Optional/Versioned Injection**: DI system does not support advanced patterns like named, optional, or versioned services.
- **No Interception/Middleware**: No built-in support for service interception (AOP/middleware).

### Recommendations
- Add APIs for named, optional, and versioned injection.
- Consider introducing interception hooks or middleware patterns for cross-cutting concerns.

---

## 8. **Documentation & Examples**

### Issues
- **Scattered Documentation**: DI documentation is split across code, README, and roadmap, with no dedicated section or end-to-end examples.

### Recommendations
- Create a dedicated DI documentation section with end-to-end examples (registration, discovery, scoping, testing, advanced usage).
- Maintain a living migration/upgrade guide as the DI system evolves.

---

## 9. **Miscellaneous**

### Issues
- **Linting/Imports**: Some files have unsorted or unused imports, and magic values in comparisons.
- **Type Safety**: Type hints are present but could be stricter (e.g., for factory functions, parameter types).

### Recommendations
- Run linting and type-checking regularly; fix all outstanding warnings.
- Enforce strict type hints for all public APIs and DI-related code.

---

# Summary

The Uno DI system is modern, robust, and already supports many best practices. Addressing the above issues and recommendations will further improve usability, maintainability, and developer experience, making Uno a top-tier choice for DDD and event-driven Python applications.

---

_Last reviewed: 2025-04-22_
