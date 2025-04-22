# Structured Logging

## Overview

Structured logging is a pattern that treats log entries as structured data rather than plain text, making logs more consistent, queryable, and machine-readable. The Uno logging system provides built-in support for structured logging.

## Benefits of Structured Logging

- **Consistency**: Enforces consistent log formats
- **Searchability**: Makes logs easier to search and filter
- **Analysis**: Enables advanced log analysis and correlation
- **Integration**: Simplifies integration with log management systems

## Using Structured Logging

### Basic Structure

All logs in Uno should include the following basic structure:

```python
logger.info("Message describing what happened", 
           extra={
               "key1": "value1",
               "key2": "value2"
           })
```

The `extra` parameter accepts a dictionary of key-value pairs that will be included in the structured log output.

### Standard Context Fields

The Uno logging system automatically adds these context fields to all logs:

- `timestamp`: ISO-8601 formatted timestamp
- `level`: Log level (DEBUG, INFO, etc.)
- `logger`: The name of the logger
- `module`: Python module where the log was generated
- `process_id`: Process ID
- `thread_id`: Thread ID
- `trace_id`: Distributed tracing ID (if available)
- `span_id`: Span ID for the current operation (if available)
- `request_id`: Unique ID for the current request (if available)
- `user_id`: ID of the current user (if available)

### Example Structured Log Output

JSON format:

```json
{
  "timestamp": "2023-10-15T14:23:45.123Z",
  "level": "INFO",
  "logger": "uno.domain.users",
  "message": "User login successful",
  "module": "users.auth",
  "process_id": 12345,
  "thread_id": 140736383676352,
  "trace_id": "abc123def456",
  "request_id": "req-789-xyz",
  "user_id": "user-456",
  "ip_address": "192.168.1.1",
  "login_method": "password"
}
```

## Best Practices

### Use Semantic Field Names

Choose field names that clearly describe their content:

```python
# Bad
logger.info("User created", extra={"a": user_id, "b": created_by})

# Good
logger.info("User created", extra={"user_id": user_id, "created_by": created_by})
```

### Use Consistent Field Names

Use the same field name for the same type of information across all logs:

```python
# Consistent field naming
logger.info("User created", extra={"user_id": "123"})
logger.info("User updated", extra={"user_id": "123", "fields_updated": ["email"]})
logger.info("User deleted", extra={"user_id": "123"})
```

### Use Appropriate Data Types

Use appropriate data types for field values:

```python
logger.info("Order processed", extra={
    "order_id": "ORD-123",  # String for IDs
    "amount": 99.95,        # Number for amounts
    "items_count": 5,       # Integer for counts
    "is_gift": True,        # Boolean for flags
    "processing_time_ms": 127,  # Integer for measurements
    "items": ["product1", "product2"]  # Array for collections
})
```

### Don't Log Sensitive Information

Never include sensitive information in logs:

```python
# Bad - includes sensitive data
logger.info("User login", extra={"username": username, "password": password})

# Good - excludes sensitive data
logger.info("User login attempt", extra={"username": username})
```

## Advanced Structured Logging

### Context Managers

Use context managers to add consistent context to all logs within a block:

```python
from uno.core.logging import logging_context

with logging_context(order_id="ORD-123", user_id="USER-456"):
    # All logs in this block will include order_id and user_id
    logger.info("Processing order")
    logger.info("Payment verified")
    logger.info("Order completed")
```

### Custom Log Processors

Create custom log processors to add computed fields:

```python
from uno.core.logging import register_log_processor

def add_performance_metrics(log_record):
    log_record["memory_usage_mb"] = get_current_memory_usage()
    log_record["cpu_usage_percent"] = get_current_cpu_usage()
    return log_record

register_log_processor(add_performance_metrics)
```

### Nested Structures

For complex data, use nested structures:

```python
logger.info("Order processed", extra={
    "order": {
        "id": "ORD-123",
        "customer": {
            "id": "CUST-456",
            "type": "premium"
        },
        "items": [
            {"id": "ITEM-1", "quantity": 2},
            {"id": "ITEM-2", "quantity": 1}
        ]
    }
})
```

## Integration with Log Management Systems

### ELK Stack (Elasticsearch, Logstash, Kibana)

JSON formatted logs can be directly indexed by Elasticsearch:

```python
# Configure for ELK
from uno.core.logging import configure_logging

configure_logging(
    format="JSON",
    handlers={
        "file": {
            "path": "/var/log/uno/application.log",
            "format": "JSON"
        }
    }
)
```

### Datadog Integration

For Datadog-specific fields:

```python
logger.info("API request processed", extra={
    "dd.trace_id": trace_id,
    "dd.span_id": span_id,
    "service": "api",
    "version": "1.2.3"
})
```

### New Relic Integration

For New Relic-specific structure:

```python
logger.info("Transaction completed", extra={
    "entity.name": "payment-service",
    "entity.type": "SERVICE",
    "duration.ms": execution_time
})
```
