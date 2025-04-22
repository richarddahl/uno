# Uno Logging System

## Introduction
The Uno logging system provides a unified approach to logging across all components of the application. This documentation covers the design principles, configuration options, and usage patterns for effectively logging in Uno applications.

## Quick Start

```python
from uno.core.logging import get_logger

# Create a logger for your module
logger = get_logger(__name__)

# Log messages at different levels
logger.info("Application started")
logger.warning("Resource running low", extra={"resource": "memory", "available": "10%"})
```

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