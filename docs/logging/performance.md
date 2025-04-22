# Logging Performance Considerations

## Overview

Logging should provide valuable insight into application behavior without significantly impacting performance. This document outlines best practices for performance-efficient logging.

## Performance Impact of Logging

Logging can impact performance in several ways:

- **CPU usage**: String formatting and JSON serialization require CPU cycles
- **Memory usage**: Creating log records and buffering them consumes memory
- **I/O operations**: Writing logs to disk or sending them over the network impacts I/O
- **Thread contention**: In multi-threaded applications, logging can create contention

## Best Practices

### Check Log Levels First

Always check if a log level is enabled before performing expensive operations:

```python
# Bad - always evaluates the expensive operation
logger.debug("User data: " + generate_detailed_report(user))

# Good - only evaluates if debug is enabled
if logger.isEnabledFor(logging.DEBUG):
    logger.debug("User data: %s", generate_detailed_report(user))
```

### Use String Formatting Correctly

Use % formatting or f-strings rather than string concatenation:

```python
# Bad - always concatenates strings
logger.info("Request " + request_id + " from user " + user_id)

# Good - delays string formatting until needed
logger.info("Request %s from user %s", request_id, user_id)

# Also good with f-strings (Python 3.6+)
logger.info(f"Request {request_id} from user {user_id}")
```

### Avoid Excessive Logging

Be strategic about what and when you log:

```python
# Bad - logging in a tight loop
for item in large_list:
    logger.debug("Processing item %s", item.id)
    process_item(item)

# Good - summarize afterwards
processed_count = 0
for item in large_list:
    process_item(item)
    processed_count += 1

logger.debug("Processed %d items", processed_count)
```

### Use Batched Logging for High-Volume Events

For high-frequency events, use the batch logging functionality:

```python
from uno.core.logging import BatchLogger

batch_logger = BatchLogger(logger, max_batch_size=100, flush_interval_seconds=5)

for item in large_dataset:
    # These logs will be collected and sent in batches
    batch_logger.info("Processed item", extra={"item_id": item.id})

# Make sure to flush any remaining logs at the end
batch_logger.flush()
```

### Configure Appropriate Log Levels

Set appropriate log levels for different environments:

```python
# Development environment
configure_logging(level="DEBUG")

# Production environment
configure_logging(level="INFO")
```

### Use Sampling for High-Volume Logs

For very high-volume operations, consider sampling logs:

```python
from uno.core.logging import sample_log

# Log only 1% of these high-volume events
for request in stream_of_requests:
    sample_log(logger.debug, 0.01, "Request details", extra={"request": request.id})
```

### Optimize JSON Serialization

Use efficient serialization for structured logging:

```python
from uno.core.logging import configure_logging

# Configure for better JSON performance
configure_logging(
    format="JSON",
    json_options={
        "serializer": "orjson",  # Faster JSON library
        "serialize_standard_types": True
    }
)
```

## Async Logging

For high-performance applications, use asynchronous logging:

```python
from uno.core.logging import configure_logging

# Configure async logging
configure_logging(
    handlers={
        "async_file": {
            "type": "async",
            "path": "/var/log/uno/application.log",
            "queue_size": 1000
        }
    }
)
```

## Measuring Logging Performance

### Benchmarking Logging Overhead

Use the built-in benchmarking tools to measure logging overhead:

```python
from uno.core.logging.benchmarks import benchmark_logging_overhead

results = benchmark_logging_overhead(
    log_level="INFO",
    message_count=10000,
    with_context=True
)
print(f"Average logging time: {results['avg_time_ms']}ms per log")
```

### Monitoring Logging Performance in Production

Configure logging performance metrics:

```python
from uno.core.logging import configure_logging

configure_logging(
    metrics_enabled=True,
    metrics_output="prometheus"
)
```

This will expose metrics such as:

- `logging_throughput`: Logs per second
- `logging_latency`: Time spent logging
- `logging_queue_size`: Size of the logging queue
- `logging_errors`: Count of logging errors

## Log Rotation and Management

Proper log rotation prevents logs from consuming too much disk space:

```python
from uno.core.logging import configure_logging

configure_logging(
    handlers={
        "file": {
            "path": "/var/log/uno/application.log",
            "rotation": {
                "max_size_mb": 100,
                "backup_count": 10,
                "compress": True
            }
        }
    }
)
```

## Memory Considerations

### Avoiding Memory Leaks

Be careful with large objects in structured logging:

```python
# Bad - may hold references to large objects
logger.info("Data processed", extra={"data": large_data_object})

# Good - only log identifiers or summaries
logger.info("Data processed", extra={
    "data_id": large_data_object.id,
    "data_size": len(large_data_object)
})
```

### Controlling Log Buffer Size

Configure appropriate buffer sizes:

```python
from uno.core.logging import configure_logging

configure_logging(
    buffer_size=10000,  # Maximum number of log records to buffer
    buffer_flush_interval=5  # Seconds between buffer flushes
)
```
