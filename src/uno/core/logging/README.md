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
from uno.core.logging import get_logger

# Create a logger for your module
logger = get_logger(__name__)

# Log messages at different levels
logger.debug("Detailed debug information")
logger.info("General information about system operation")
logger.warning("Warning about potential issues")
logger.error("Error information when something fails")
logger.critical("Critical error that requires immediate attention")

# Logging with context data
logger.info("User login successful", extra={"user_id": "123", "ip_address": "192.168.1.1"})
```

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

- Logger instances are cached using `lru_cache` with a max size of 16
- Root logger configuration is cached to avoid redundant setup

## Advanced Usage

For advanced usage patterns, custom log handlers, and integration with monitoring systems, refer to the [detailed logging documentation](../../../docs/logging/index.md).