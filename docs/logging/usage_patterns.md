# Logging Usage Patterns

**LoggerService via DI is the recommended way to use logging in Uno. Legacy get_logger is fallback only.**

This document demonstrates best practices for using Uno logging in your apps and packages.

## DI-First Logger Injection (Recommended)

### In Services

Inject `LoggerService` via the constructor and use it to get a logger:

```python
from uno.core.logging.logger import LoggerService

class MyService:
    def __init__(self, logger_service: LoggerService):
        self._logger = logger_service.get_logger(__name__)

    def do_something(self):
        self._logger.info("Did something!")
```

### In Scripts

```python
from uno.core.logging.logger import LoggerService
import asyncio

logger_service = LoggerService()
asyncio.run(logger_service.initialize())
logger = logger_service.get_logger("my_script")
logger.info("Script started")
```

### In Tests

```python
import pytest
from uno.core.logging.logger import LoggerService

@pytest.fixture
def logger_service():
    svc = LoggerService()
    import asyncio; asyncio.run(svc.initialize())
    yield svc
    asyncio.run(svc.dispose())

def test_logging(logger_service, caplog):
    logger = logger_service.get_logger("test")
    with caplog.at_level("INFO"):
        logger.info("Test log")
    assert any("Test log" in msg for msg in caplog.messages)
```

## Basic Logging

### Using Log Levels Appropriately

- **DEBUG**: Detailed information, typically useful only for diagnosing problems

  ```python
  logger.debug("Connecting to database at %s:%s", host, port)
  ```

- **INFO**: Confirmation that things are working as expected

  ```python
  logger.info("User %s successfully authenticated", user_id)
  ```

- **WARNING**: An indication that something unexpected happened, or may happen in the near future

  ```python
  logger.warning("API rate limit at 90% (%s/%s requests)", current, limit)
  ```

- **ERROR**: Due to a more serious problem, the software has not been able to perform a function

  ```python
  logger.error("Failed to process payment", extra={"order_id": order_id, "error_code": error_code})
  ```

- **CRITICAL**: A serious error indicating that the program itself may be unable to continue running

  ```python
  logger.critical("Database connection lost, application cannot function")
  ```

## Structured Logging

### Adding Context to Logs

Always include relevant context with your logs:

```python
# Bad - lacks context
logger.info("Order processed")

# Good - includes order context
logger.info("Order processed", extra={"order_id": "12345", "amount": 99.95, "currency": "USD"})
```

### Using Consistent Keys

Use consistent keys for common entities across your application:

```python
# User-related logs
logger.info("User profile updated", extra={"user_id": "123", "fields_updated": ["name", "email"]})

# Order-related logs
logger.info("Order shipped", extra={"order_id": "456", "user_id": "123", "shipping_method": "express"})
```

## Contextual Logging

### Using Context Managers

Use context managers to add consistent context to multiple log statements:

```python
from uno.core.logging import logging_context

# Add context for a block of code
with logging_context(user_id="123", request_id="req-456"):
    logger.info("Operation started")
    # ... more operations that will include the context
```

### Decorators for Context

Use decorators to automatically add context to functions:

```python
from uno.core.logging import with_error_context

@with_error_context
async def process_request(request_data):
    logger.info("Processing request")
    # ... processing logic
```

## Error Logging

### Logging Exceptions

Always include exception information when logging errors:

```python
try:
    # Some operation that might fail
    result = process_data(data)
except Exception as e:
    logger.exception("Failed to process data")  # Automatically includes traceback
    # or
    logger.error("Failed to process data", exc_info=True)  # Explicitly include traceback
    # or with additional context
    logger.error("Failed to process data", exc_info=True, 
                extra={"data_id": data.id, "error_type": type(e).__name__})
```

## Performance Considerations

### Check Log Levels First

Always check if a log level is enabled before performing expensive operations:

```python
# Bad - always evaluates the expensive operation
logger.debug("User data: " + generate_detailed_report(user))

# Good - only evaluates if debug is enabled
if logger.isEnabledFor(logging.DEBUG):
    logger.debug("User data: %s", generate_detailed_report(user))
```

## Integration with Application Features

### Request Logging

Integrate with web request handling:

```python
from uno.core.logging import RequestLoggingMiddleware

# In your web framework setup
app.add_middleware(RequestLoggingMiddleware)
```

### Database Operation Logging

Log database operations:

```python
from uno.core.logging import DatabaseLoggingMiddleware

# In your database setup
engine = create_engine(db_url)
DatabaseLoggingMiddleware.setup(engine)
```

### Audit Logging

For security-sensitive operations:

```python
from uno.core.logging import audit_log

# Log security-relevant actions with special handling
audit_log.info("User permission changed", 
              extra={"user_id": user.id, 
                    "permission": permission,
                    "changed_by": admin.id,
                    "reason": reason})
```
