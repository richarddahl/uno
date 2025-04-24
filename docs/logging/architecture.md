# Logging System Architecture

## Overview

The Uno logging system is built on top of Python's standard logging module with extensions to support structured logging, contextual information, and various output formats.

## Core Components

### Logger Factory

The `LoggerService` class, provided via dependency injection, is the primary entry point for obtaining logger instances. It ensures consistent configuration and behavior across all loggers in the application. Use DI to inject `LoggerService` into your services or scripts:

```python
from uno.core.logging.logger import LoggerService

class MyService:
    def __init__(self, logger_service: LoggerService):
        self._logger = logger_service.get_logger(__name__)
```

The legacy `get_logger` function is available for backward compatibility but should not be used in new code.

### Log Record Enhancers

Log record enhancers add additional context to log entries, such as:

- Request ID
- User information
- Execution context
- Environment information

### Log Handlers

Multiple handlers can be configured to direct logs to different destinations:

- Console output
- File logging
- Syslog
- Cloud logging services
- Metrics systems

### Formatters

Formatters control how log records are converted to output strings:

- Text formatters for human-readable logs
- JSON formatters for machine-readable logs
- Custom formatters for specific integrations

## Architecture Diagram

```
┌───────────────┐     ┌────────────────┐     ┌──────────────┐
│ Application   │────▶│ Logger Factory │────▶│ Logger       │
└───────────────┘     └────────────────┘     └──────────────┘
                                                      │
                                                      ▼
┌───────────────┐     ┌────────────────┐     ┌──────────────┐
│ Log Record    │◀────│ Log Filters    │◀────│ Log Record   │
│ Enhancers     │     │                │     │              │
└───────────────┘     └────────────────┘     └──────────────┘
        │                                             ▲
        ▼                                             │
┌───────────────┐     ┌────────────────┐     ┌──────────────┐
│ Formatters    │────▶│ Handlers       │────▶│ Output       │
└───────────────┘     └────────────────┘     │ Destinations │
                                              └──────────────┘
```

## Integration Points

The logging system is integrated with:

- Configuration system for dynamic configuration
- Context management for contextual logging
- Error handling for automatic error logging
- Performance monitoring for log-based metrics

## Configuration System

The logging system uses a hierarchical configuration system:

1. Environment variables (highest priority)
2. Pydantic settings classes (Dev, Test, Prod)
3. Default values defined in `LoggingConfig`

The configuration is automatically loaded based on the `ENV` environment variable (defaults to "dev").
