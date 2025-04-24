# Uno Core Logging Module

## Overview

The Core Logging module provides a standardized logging framework for the Uno application. It offers consistent logging patterns, configurable log levels, and structured logging capabilities to help with debugging, monitoring, and troubleshooting.

**Integration with Dependency Injection (DI):**

Uno's logging system is tightly integrated with the DI system (`uno.core.di`). This allows logger instances to be injected into your services, ensuring consistent configuration and making your code more testable and modular. See the "Logger Injection via DI" section below.

## Features

- Standardized logging interface across all Uno components
- Configurable log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Structured logging with context data
- Integration with various logging backends
- Performance optimized logging implementation

## Basic Usage

You can obtain a logger directly using `get_logger`, or (preferred) via dependency injection:

```python
from uno.core.logging import get_logger

# Direct (non-DI) usage
logger = get_logger(__name__)
logger.info("Direct logger usage is supported but DI is preferred in Uno apps.")
```

### Logger Injection via DI (Recommended)

When building services or components managed by Uno's DI system, inject the logger as a dependency:

```python
from uno.core.di import ServiceProvider
import logging

class MyService:
    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def do_something(self) -> None:
        self._logger.info("Service action executed")

# In your DI configuration (usually handled by Uno):
# The DI container automatically provides a logger instance.
service_provider = ServiceProvider()
my_service = service_provider.get_service(MyService)
```

> **Tip:** The DI container registers a singleton logger (configured by uno.core.logging) so all injected loggers are consistent and ready to use.

## Configuration

Logging configuration is handled through the application's configuration system. See the [detailed logging documentation](../../../docs/logging/index.md) for complete configuration options.

When using DI, the logger you receive is already configured according to your environment and application settings.

## Advanced Usage

For advanced usage patterns, custom log handlers, and integration with monitoring systems, refer to the [detailed logging documentation](../../../docs/logging/index.md).

For more about DI and logger injection, see [docs/logging/usage_patterns.md](../../../docs/logging/usage_patterns.md) and [docs/logging/architecture.md](../../../docs/logging/architecture.md).