# Logging System Architecture

## Overview

The Uno logging system is built on top of Python's standard logging module with extensions to support structured logging, contextual information, and various output formats.

## Core Components

### Logger Factory and DI Integration

The `get_logger` function serves as the primary entry point for obtaining logger instances. In Uno applications, logger instances are typically provided via the DI system, ensuring consistent configuration and making logger injection the preferred pattern for all services and components.

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
┌───────────────┐
│   DI System   │  (Injects loggers into services/components)
└───────────────┘
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

> **Note:** The DI system is a central integration point for logger provisioning in Uno.

## Integration Points

The logging system is integrated with:

- **Dependency Injection (DI) system** for providing logger instances to all services and components
- Configuration system for dynamic configuration
- Context management for contextual logging
- Error handling for automatic error logging
- Performance monitoring for log-based metrics

## Extension Points

The logging system can be extended through:

- Custom log handlers
- Custom formatters
- Log record enhancers
- Logging middleware components
