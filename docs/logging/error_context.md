# Uno Logging: Error Context

## Overview
Uno's logging system supports rich error context injection in all log records. This includes exception info, error codes, stack traces, and arbitrary context fields.

## How to Log Errors

### Using structured_log
```python
try:
    ...
except Exception as exc:
    logger_service.structured_log(
        "error",
        "Failed to process request",
        exc_info=exc,
        error_context={"error_code": "PROC_ERR", "user_id": "abc123"},
    )
```

### Using ErrorLoggingService
```python
from uno.core.logging.error_logging_service import ErrorLoggingService
error_service = ErrorLoggingService(logger_service)
try:
    ...
except Exception as exc:
    error_service.log_error(exc, context={"user_id": "abc123"})
```

## Error Context Fields
- `exception_type`, `exception_message`, `exception_traceback`: always included if `exc_info` is provided
- `error_code`, `error_message`: for framework errors or when set via `error_context`
- Arbitrary fields: add any extra context needed

## Output Formats
- Error context is present in both standard and JSON log output
- Field names match Uno's logging schema for easy parsing
