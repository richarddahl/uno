# LoggerService to LoggerProtocol/get_logger Migration Guide

## Overview

This document outlines the migration path from the legacy `LoggerService` class to the new `LoggerProtocol` and `get_logger` based logging system in the Uno framework.

## Background

The Uno framework is transitioning to a more flexible, protocol-based logging system. This change:

- Replaces concrete `LoggerService` implementations with a `LoggerProtocol` interface
- Introduces a `get_logger()` factory function for obtaining logger instances
- Aligns with Python 3.13 type annotation standards and Protocol-based design
- Improves testability through better interface-based design

## Migration Steps

### Automated Migration

1. **Run the Migration Script**

   ```bash
   cd /Users/richarddahl/Code/uno
   ./src/scripts/migrate_logger_service.py
   ```

   This script automatically replaces:
   - Import statements (`from uno.logging import LoggerService` → `from uno.logging import LoggerProtocol, get_logger`)
   - Type annotations (`logger: LoggerService` → `logger: LoggerProtocol`)
   - Constructor calls (`LoggerService(name)` → `get_logger(name)`)

2. **Verify the Migration**

   ```bash
   ./src/scripts/verify_logger_migration.py
   ```

   This script checks for any remaining references to `LoggerService` that might need manual attention.

### DI Container Changes

If you're using the DI container, update your registrations:

```python
# Before
container.register_singleton(LoggerService, lambda: LoggerService("app"))

# After
container.register_singleton(LoggerProtocol, lambda: get_logger("app"))
```

### Manual Changes Required

The following cases require manual intervention:

1. **Complex LoggerService instantiations** with custom parameters
2. **Subclasses of LoggerService** - these should be updated to implement `LoggerProtocol`
3. **Factory methods** that return `LoggerService` instances

## Code Examples

### Example 1: Basic Usage

```python
# Before
from uno.logging import LoggerService

logger = LoggerService("my_module")
logger.info("Hello world")

# After
from uno.logging import get_logger

logger = get_logger("my_module")
logger.info("Hello world")
```

### Example 2: Method Parameters

```python
# Before
def process_data(data: dict, logger: LoggerService) -> None:
    logger.info("Processing data")

# After
def process_data(data: dict, logger: LoggerProtocol) -> None:
    logger.info("Processing data")
```

### Example 3: Class Constructor

```python
# Before
class DataProcessor:
    def __init__(self, logger: LoggerService) -> None:
        self.logger = logger

# After
class DataProcessor:
    def __init__(self, logger: LoggerProtocol) -> None:
        self.logger = logger
```

## Troubleshooting

If you encounter issues after migration:

1. **Type errors**: Ensure all imports and type annotations are correctly updated
2. **Missing methods**: Check that you're using methods defined in `LoggerProtocol`
3. **DI container errors**: Verify that the DI container is properly configured to resolve `LoggerProtocol`

## Best Practices

- **Use type annotations** consistently with `LoggerProtocol`
- **Inject loggers** rather than creating them directly in methods
- **Use context managers** for adding context to log entries: `with logger.context(request_id=id):`
- **Create bound loggers** with `logger.bind()` for component-specific logging

## Timeline

- **May 2025**: Begin migration across the codebase
- **June 2025**: All code should be using the new logging system
- **July 2025**: `LoggerService` class will be deprecated
- **September 2025**: `LoggerService` class will be removed

## Additional Resources

- See `uno/logging/protocols.py` for the full `LoggerProtocol` definition
- See `uno/logging/logger.py` for the `get_logger` implementation
- Refer to the test examples in `test_no_result.py` for usage examples
