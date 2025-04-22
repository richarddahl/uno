# Refactoring `get_logger` Usage in Uno

## Background

The Uno codebase previously used direct calls to `get_logger` from `uno.core.logging.logger` in various modules and components. To improve consistency, maintainability, and testability, logger instances should be retrieved via the Dependency Injection (DI) system rather than being instantiated directly in each module.

## Identified Locations of Direct `get_logger` Usage

The following files were found to use `get_logger` directly:

1. `src/uno/core/infrastructure/sql/emitter.py`
2. `src/uno/core/infrastructure/sql/observers.py`
3. `src/uno/core/application/fastapi_error_handlers.py`
4. `src/uno/examples/todolist/application/event_handlers.py`
5. `src/uno/examples/todolist/application/middleware.py`

## Refactoring Plan

- **Objective:** Replace all direct usages of `get_logger` with logger injection via DI or function arguments.
- **Approach:**
  - For classes, add a `logger` argument to the constructor (with a default if needed).
  - For functions or modules, require a logger argument or inject via DI where possible.
  - Remove all direct imports and calls to `get_logger` in these modules.

## Benefits

- **Consistency:** All loggers are managed through the DI system.
- **Testability:** Easier to mock or swap loggers during testing.
- **Maintainability:** Centralizes logger configuration and reduces coupling.

## Next Steps

- Refactor the above files to use DI-based logger retrieval.
- Update tests and documentation as needed.
- Ensure the application and tests run without issues after refactoring.

---

*This document will be updated as refactoring progresses and will include code examples and migration notes once the changes are complete.*
