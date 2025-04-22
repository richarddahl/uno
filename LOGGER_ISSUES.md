# Logger Usage Issues and Audit

## Summary
This document records findings from an audit of logger usage in the Uno codebase, focusing on whether loggers are provided via dependency injection (DI) or obtained directly via `get_logger` imports/calls.

---

## Key Principle
- **In a DI-driven system, loggers should be injected by the DI container, not imported or instantiated directly in business logic.**
- The only places that should directly call or import `get_logger` are DI configuration/registration code and possibly utility scripts/tests.

---

## Findings

### 1. Correct Usage (DI-driven)
- Many core classes and services accept a `logger` parameter and are provided a logger via the DI system. This is the correct pattern.
- Example: `ServiceProvider`, `QueryCache`, and others accept `logger: logging.Logger = None` and default to a logger if not provided.

### 2. Direct Imports/Calls to `get_logger`
- **DI configuration code:**
  - In `src/uno/core/di/provider.py`, loggers are registered for services using `get_logger`. This is appropriate.
- **Business logic and service classes:**
  - There are no remaining direct imports or calls to `get_logger` in business logic or service classes after recent refactors.
- **In tests:**
  - The test suite (`tests/core/logging/test_logger.py`) imports and calls `get_logger` directly. This is acceptable for testing the logger system itself.
- **In DI container code:**
  - The top-level import of `get_logger` in `src/uno/core/di/container.py` was removed to break a circular import. There are currently no direct calls to `get_logger` in this file.

### 3. Circular Import Issue
- A circular import was detected:
  - `uno.core.logging.logger` → `uno.config.logging` → `uno.core.di` → `uno.core.di.container` → `uno.core.logging.logger`
  - This was caused by a top-level import of `get_logger` in `container.py`. The fix was to remove the top-level import and only import `get_logger` inside functions if needed (though currently, it's not needed at all in this file).

### 4. Recommendations
- **Maintain the pattern:** Only import/call `get_logger` in DI configuration/registration code, not in business logic.
- **If a logger is needed in a class/function, always inject it via DI.**
- **If you must use `get_logger` outside DI (e.g., in a script or test), document the reason.**
- **Continue to avoid top-level imports of `get_logger` in modules that are part of the DI cycle.**

---

## Action Items
- ✅ Remove top-level imports of `get_logger` from business logic and DI container code.
- ✅ Ensure all logger usage in services and business logic is DI-driven.
- ✅ Document this audit and keep it up to date as the codebase evolves.

---

_No further direct imports of `get_logger` in business logic were found. The DI system is now the sole provider of loggers in application code._
