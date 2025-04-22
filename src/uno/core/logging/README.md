# Uno Core Logging Module

## Overview

The Core Logging module provides a standardized logging framework for the Uno application. It offers consistent logging patterns, configurable log levels, and structured logging capabilities to help with debugging, monitoring, and troubleshooting.

## Features

- Standardized logging interface across all Uno components
- Configurable log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Structured logging with context data
- Integration with various logging backends
- Performance optimized logging implementation

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

Logging configuration is handled through the application's configuration system. See the [detailed logging documentation](../../../docs/logging/index.md) for complete configuration options.

## Advanced Usage

For advanced usage patterns, custom log handlers, and integration with monitoring systems, refer to the [detailed logging documentation](../../../docs/logging/index.md).