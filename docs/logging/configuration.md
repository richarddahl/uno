# Logging Configuration

## Overview

The Uno logging system is highly configurable to support different environments, output formats, and logging levels. Configuration can be specified through environment variables, configuration files, or programmatically.

## Basic Configuration

### Environment Variables

The following environment variables control logging behavior:

- `UNO_LOG_LEVEL`: Sets the global log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `UNO_LOG_FORMAT`: Sets the log format (TEXT, JSON, PRETTY)
- `UNO_LOG_OUTPUT`: Sets where logs are sent (CONSOLE, FILE, BOTH)
- `UNO_LOG_FILE`: Path to the log file when file logging is enabled
- `UNO_LOG_INCLUDE_TIMESTAMP`: Whether to include timestamps (TRUE, FALSE)

### Configuration File

Logging can be configured in the application config file:

```yaml
logging:
  level: INFO
  format: JSON
  output: CONSOLE
  file_path: /var/log/uno/application.log
  include_timestamp: true
  structured: true
  handlers:
    console:
      enabled: true
      level: INFO
    file:
      enabled: true
      level: DEBUG
      path: /var/log/uno/application.log
      rotation:
        max_size_mb: 100
        backup_count: 10
    syslog:
      enabled: false
      facility: local0
  loggers:
    uno.core:
      level: INFO
    uno.domain:
      level: DEBUG
    sqlalchemy:
      level: WARNING
```

## Advanced Configuration

### Programmatic Configuration

For more complex setups, logging can be configured programmatically:

```python
from uno.core.logging import configure_logging

configure_logging(
    level="INFO",
    format="JSON",
    output="BOTH",
    file_path="/var/log/uno/application.log",
    include_timestamp=True,
    structured=True,
    handlers={
        "console": {"enabled": True, "level": "INFO"},
        "file": {
            "enabled": True, 
            "level": "DEBUG",
            "path": "/var/log/uno/application.log",
            "rotation": {"max_size_mb": 100, "backup_count": 10}
        }
    },
    loggers={
        "uno.core": {"level": "INFO"},
        "uno.domain": {"level": "DEBUG"},
        "sqlalchemy": {"level": "WARNING"}
    }
)
```

### Custom Handlers

You can register custom log handlers:

```python
from uno.core.logging import register_handler
from my_monitoring import MonitoringLogHandler

monitor_handler = MonitoringLogHandler(endpoint="https://monitoring.example.com/logs")
register_handler("monitoring", monitor_handler, level="WARNING")
```

## Environment-Specific Configurations

### Development

For development environments, we recommend:

```yaml
logging:
  level: DEBUG
  format: PRETTY
  output: CONSOLE
  structured: false
```

### Production

For production environments, we recommend:

```yaml
logging:
  level: INFO
  format: JSON
  output: BOTH
  file_path: /var/log/uno/application.log
  structured: true
  handlers:
    console:
      enabled: true
      level: INFO
    file:
      enabled: true
      level: INFO
      rotation:
        max_size_mb: 100
        backup_count: 10
```

### Testing

For testing environments, we recommend:

```yaml
logging:
  level: CRITICAL  # Minimize logging output during tests
  output: CONSOLE
  format: TEXT
```
