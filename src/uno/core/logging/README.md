# Uno Core Logging

## Overview
Uno's core logging module provides structured, high-performance, and context-rich logging for all Uno applications. It is fully dependency-injection (DI) compatible and supports runtime configuration, error context, trace/correlation IDs, and both standard and JSON log output.

## Features
- DI-injected `LoggerService` for all logging needs
- Structured logging with arbitrary context fields
- Trace/correlation/request ID propagation for distributed tracing
- Error context injection (exception info, error codes, stack traces)
- Runtime config via `LoggingConfigService` (log level, format, output)
- JSON and standard log output, dynamic reload
- CLI/admin integration for live config updates

## Quick Start
```python
from uno.core.logging.logger import LoggerService
from uno.core.logging.config_service import LoggingConfigService

# Dependency injection (recommended)
logger_service = LoggerService()
logger_service.initialize()
logger = logger_service.get_logger("my.module")

# Structured/context logging
logger_service.structured_log(
    "info",
    "User login",
    user_id="abc123",
    trace_context={"correlation_id": "..."},
    error_context={"error_code": "AUTH_FAIL"},
)

# Trace context propagation
with logger_service.trace_scope(logger_service):
    logger.info("Inside a trace scope!")

# Error logging
from uno.core.logging.error_logging_service import ErrorLoggingService
error_service = ErrorLoggingService(logger_service)
try:
    ...
except Exception as exc:
    error_service.log_error(exc, context={"user_id": "abc123"})

# Runtime config
config_service = LoggingConfigService(logger_service)
config_service.set_level("DEBUG")
config_service.set_json_format(True)
```

## CLI Usage
You can update logging config at runtime via the Uno admin/CLI (see docs/logging/cli.md).

## Best Practices
- Always inject `LoggerService` via DI for testability and consistency.
- Use `structured_log` for all logs with context.
- Use `trace_scope` for request/operation tracing.
- Use `ErrorLoggingService` for error events.
- Use `LoggingConfigService` for runtime config.

See [docs/logging/](../../../docs/logging/) for full developer documentation and advanced usage.
