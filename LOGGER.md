# Central Logging Refactor Checklist

This document lists all places in the codebase that must be updated to use the dependency-injected central logging system via `get_logger` from `uno.core.logging.logger`.

## Why?
To ensure all logging is consistent, configurable, and testable, all loggers should be obtained via the central logger abstraction, not by direct calls to `logging.getLogger` or other logging configuration code.

---

## Locations to Update

### 1. Direct use of `logging.getLogger` as a default logger

- **src/uno/core/infrastructure/database/query_cache.py**
  - `QueryCache.__init__`: `self.logger = logger or logging.getLogger(__name__)`
- **src/uno/core/infrastructure/database/engine/__init__.py**
  - `DatabaseFactory.__init__`: `self.logger = logger or logging.getLogger(__name__)`
- **src/uno/core/infrastructure/database/engine/base.py**
  - `EngineFactory.__init__`: `self.logger = logger or logging.getLogger(__name__)`
- **src/uno/core/infrastructure/database/enhanced_connection_pool.py**
  - `EnhancedAsyncConnectionManager.__init__`: `self.logger = logger or logging.getLogger(__name__)`
- **src/uno/core/infrastructure/sql/observers.py**
  - `LoggingSQLObserver.__init__`: `self.logger = logger or logging.getLogger(__name__)`
- **src/uno/core/di/provider.py**
  - `ServiceProvider.__init__`: `self._logger = logger or logging.getLogger("uno.services")`

### 2. Direct use of `logging.basicConfig` or custom setup

- **src/scripts/db_init.py**
  - `setup_logging`: Calls `logging.basicConfig(...)` directly. Should use central configuration.

### 3. Any other direct use of the standard logging module

- Search for any other use of `logging.getLogger`, `logging.basicConfig`, or log methods (`logging.info`, `logging.warning`, etc.) outside of `uno/core/logging/logger.py` and update them to use the central system.

---

## How to Update
- Replace all `logging.getLogger(...)` default loggers with `get_logger(...)` from `uno.core.logging.logger`.
- Ensure logger dependency injection uses `get_logger` as the default.
- Remove or refactor any direct calls to `logging.basicConfig` in favor of the central configuration.

---

## Example Refactor

**Before:**
```python
self.logger = logger or logging.getLogger(__name__)
```

**After:**
```python
from uno.core.logging.logger import get_logger
self.logger = logger or get_logger(__name__)
```

---

Review this list and update each location to ensure all logging is routed through the central logger abstraction.
