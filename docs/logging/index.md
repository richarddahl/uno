# Uno Logging Developer Documentation

## Introduction
Uno's logging system is designed for modern, scalable, and testable applications. It provides DI-based logger injection, structured and JSON logging, runtime configuration, error context, tracing, and CLI/admin integration.

## Table of Contents
- [Overview](#overview)
- [Dependency Injection](#dependency-injection)
- [Structured Logging](#structured-logging)
- [Trace/Correlation IDs](#tracecorrelation-ids)
- [Error Context](#error-context)
- [Runtime Configuration](#runtime-configuration)
- [CLI/Admin Integration](#cliadmin-integration)
- [Best Practices](#best-practices)

## Overview
- All logging is handled by DI-injected `LoggerService`.
- Supports structured context fields, trace/correlation IDs, and error context.
- Configurable at runtime via `LoggingConfigService` and CLI.

## Dependency Injection
```python
from uno.core.logging.logger import LoggerService
logger_service = LoggerService(...)
logger_service.initialize()
logger = logger_service.get_logger("my.module")
```
- Inject `LoggerService` into all services/components.

## Structured Logging
```python
logger_service.structured_log(
    "info",
    "User updated profile",
    user_id="abc123",
    changes={"email": "new@example.com"},
)
```
- Use key/value pairs for rich log context.

## Trace/Correlation IDs
```python
with logger_service.trace_scope(logger_service):
    logger.info("Operation in trace scope")
```
- Use `trace_scope` to propagate correlation/request IDs.
- Use `new_trace_context()` to generate new IDs.

## Error Context
```python
try:
    ...
except Exception as exc:
    logger_service.structured_log(
        "error",
        "Failed to process request",
        exc_info=exc,
        error_context={"error_code": "PROC_ERR"},
    )
```
- Use `error_context` and `exc_info` for full exception details.
- Or use `ErrorLoggingService.log_error()` for convenience.

## Runtime Configuration
```python
from uno.core.logging.config_service import LoggingConfigService
config_service = LoggingConfigService(logger_service)
config_service.set_level("DEBUG")
config_service.set_json_format(True)
```
- Change log level, format, outputs live at runtime.

## CLI/Admin Integration
- Logging config can be managed via the Uno CLI/admin tools.
- See [cli.md](cli.md) for full CLI usage and commands.

## Best Practices
- Always use DI for logger access.
- Prefer `structured_log` and context fields.
- Use `trace_scope` for tracing.
- Use `ErrorLoggingService` for error events.
- Use runtime config for live tuning.
