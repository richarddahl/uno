# Logging Usage Patterns

## Basic Logging

### Getting a Logger
Always get a logger for your module using the `get_logger` function:

```python
from uno.core.logging import get_logger

# Use the module name as the logger name
logger = get_logger(__name__)
```

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

# All logs within this block will have the specified context added
with logging_context(request_id="abc-123", user_id="user-456"):
    logger.info("Processing request")
    # ... code that produces more logs ...
    logger.info("Request completed")
```

### Function and Request Contexts
Use decorators to add consistent context to all logs within a function:

```python
from uno.core.logging import with_logging_context

@with_logging_context(component="payment_processor")
def process_payment(order_id, amount):
    logger.info("Starting payment processing", extra={"order_id": order_id, "amount": amount})
    # ... payment processing code ...
    logger.info("Payment processing completed")
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

### Logging with Traceback Control
Control traceback inclusion based on log level:

```python
from uno.core.logging import log_error

# Logs at ERROR level with traceback, or WARNING level without traceback
log_error(logger, "Operation partially failed", exception=exc, 
          is_error=is_critical,  # If True, logs at ERROR level with traceback
          extra={"operation": "data_sync"})
```

## Performance Considerations

### Expensive Operations in Logs
Use lazy evaluation for expensive operations:

```python
# Bad - always generates the expensive string representation
logger.debug("User data: " + str(user_data))

# Good - only generates if debug is enabled
logger.debug("User data: %s", user_data)

# Better - explicitly check log level for very expensive operations
if logger.isEnabledFor(logging.DEBUG):
    detailed_data = generate_detailed_report(user_data)  # Expensive operation
    logger.debug("Detailed report: %s", detailed_data)
```

### Batch Logging
For high-frequency logs, consider batching:

```python
from uno.core.logging import BatchLogger

batch_logger = BatchLogger(logger, max_batch_size=100, flush_interval_seconds=5)

for item in large_dataset:
    # These logs will be collected and sent in batches
    batch_logger.info("Processed item", extra={"item_id": item.id})

# Make sure to flush any remaining logs at the end
batch_logger.flush()
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