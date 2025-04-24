# Uno Logging System

## Introduction

Uno provides a robust, extensible logging system designed for modern, scalable Python applications. It supports structured logging, context propagation, and flexible configuration for both development and production environments.

## Recommended Usage: Dependency Injection (DI-First)

The preferred way to use logging in Uno is via dependency injection. Inject `LoggerService` into your services, modules, or scripts:

### Logger Injection via Dependency Injection (DI)

Uno's DI system automatically provides logger instances for your services and components. This is the preferred pattern for production Uno applications:

```python
import logging
from uno.core.di import ServiceProvider

class MyService:
    def __init__(self, logger: logging.Logger):
        self._logger = logger
    def do_work(self) -> None:
        self._logger.info("Work started")

service_provider = ServiceProvider()
my_service = service_provider.get_service(MyService)
```

> **See also:** [Usage Patterns](usage_patterns.md#injecting-loggers-via-di) and [Architecture](architecture.md#integration-points)

## Table of Contents

1. [Architecture](architecture.md)
2. [Configuration](configuration.md)
3. [Usage Patterns](usage_patterns.md)
4. [Structured Logging](structured_logging.md)
5. [Performance Considerations](performance.md)
6. [Integration with Monitoring Tools](monitoring_integration.md)
7. [Testing and Mocking](testing.md)
8. [Troubleshooting](troubleshooting.md)

## Core Principles

- **Consistency**: Provide a consistent logging interface across all components
- **Structured**: Support for structured logging with contextual information
- **Configurable**: Flexible configuration options for different environments
- **Performance**: Minimal overhead, especially for disabled log levels
- **Integration**: Easy integration with external monitoring and alerting systems