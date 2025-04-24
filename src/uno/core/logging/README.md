# Uno Core Logging Module

## Overview

The Core Logging module provides a standardized logging framework for the Uno application. It offers consistent logging patterns, configurable log levels, and structured logging capabilities to help with debugging, monitoring, and troubleshooting.

## Features

- Standardized logging interface across all Uno components
- Configurable log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Structured logging with context data
- Environment-based configuration
- Performance-optimized with caching

## Basic Usage

```python
from uno.core.logging.logger import LoggerService

# Dependency-injected usage (recommended)
logger_service = LoggerService()
import asyncio; asyncio.run(logger_service.initialize())
logger = logger_service.get_logger(__name__)

logger.info("Hello from Uno!")

# Legacy usage (not recommended, for compatibility only)
from uno.core.logging.logger import get_logger
logger = get_logger(__name__)
logger.info("Hello from Uno!")

# Structured/context logging
logger.info("User login", extra={"user_id": "123", "ip_address": "192.168.1.1"})

# In tests (pytest):
def test_logging_with_caplog(logger_service, caplog):
    logger = logger_service.get_logger("my.module")
    with caplog.at_level("INFO"):
        logger.info("Test log message")
    assert any("Test log message" in msg for msg in caplog.messages)


## Configuration

Logging configuration is managed through environment variables and Pydantic settings:

- `ENV`: Environment name (dev, test, prod) - defaults to "dev"
- `UNO_LOG_LEVEL`: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `UNO_LOG_FORMAT`: Log format string
- `UNO_LOG_DATE_FORMAT`: Date format string
- `UNO_LOG_JSON_FORMAT`: Enable JSON format (true/false)
- `UNO_LOG_CONSOLE_OUTPUT`: Enable console output (true/false)
- `UNO_LOG_FILE_OUTPUT`: Enable file output (true/false)
- `UNO_LOG_FILE_PATH`: Path to log file
- `UNO_LOG_BACKUP_COUNT`: Number of backup log files
- `UNO_LOG_MAX_BYTES`: Maximum size of log file in bytes
- `UNO_LOG_PROPAGATE`: Enable log propagation (true/false)
- `UNO_LOG_INCLUDE_LOGGER_CONTEXT`: Include logger context (true/false)
- `UNO_LOG_INCLUDE_EXCEPTION_TRACEBACK`: Include exception tracebacks (true/false)

## Performance Considerations

The logging system uses caching to optimize performance:

- Logger instances are managed and cached internally by `LoggerService` for efficiency
- Root logger configuration is initialized once per application lifecycle

## Advanced Usage

For advanced usage patterns, custom log handlers, and integration with monitoring systems, refer to the [detailed logging documentation](../../../docs/logging/index.md).