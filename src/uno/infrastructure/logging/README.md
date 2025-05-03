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

## DI Logging Best Practices

- **Always inject `LoggerService` via DI** (never use `logging.getLogger` or global loggers).
- **Pass the DI logger to all event infra** (event bus, registry, decorators).
- **Do not rely on fallback/default loggers**—make logger a required dependency.

### Example: Registering a Handler with DI Logger

```python
from uno.core.logging.logger import LoggerService, LoggingConfig
from uno.core.events.handlers import EventHandler, EventHandlerRegistry
from uno.core.events.decorators import handles

logger = LoggerService(LoggingConfig())
registry = EventHandlerRegistry(logger)

@handles(UserCreatedEvent, logger)
class UserCreatedHandler(EventHandler):
    def __init__(self):
        self.logger = logger
    async def handle(self, context: EventHandlerContext) -> Result[None, Exception]:
        event = context.event
        self.logger.structured_log("INFO", f"User created: {event.user_id}")
        return Success(None)
```

### Anti-Patterns (DO NOT)

- Do **not** use `logging.getLogger` or global loggers in handlers or event infra.
- Do **not** instantiate event infra (bus, registry, decorators) without providing a DI logger.
- Do **not** rely on fallback or default loggers.

## Testing Handlers With DI Logger

Use a mock or fake `LoggerService` for testing handler logging:

```python
import pytest
from uno.core.logging.logger import LoggerService
from uno.core.events.handlers import EventHandler

class FakeLoggerService(LoggerService):
    def __init__(self):
        self.logged = []
    def structured_log(self, level: str, message: str, **kwargs):
        self.logged.append((level, message, kwargs))

@pytest.fixture
def fake_logger():
    return FakeLoggerService()

def test_handler_logs(fake_logger):
    class MyHandler(EventHandler):
        def __init__(self):
            self.logger = fake_logger
        async def handle(self, context):
            self.logger.structured_log("INFO", "test")
            return None
    handler = MyHandler()
    # Simulate call
    import asyncio
    asyncio.run(handler.handle(None))
    assert fake_logger.logged[0][1] == "test"
```

See [docs/logging/](../../../docs/logging/) for full developer documentation and advanced usage.
