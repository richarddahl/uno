# Uno Logging CLI/Admin Integration

## Overview
The Uno CLI provides commands to inspect and update logging configuration at runtime. This enables live tuning of log levels, formats, and outputs without restarting your application.

## Commands

### Show Current Logging Config
```
uno logging config show
```

### Get/Set Individual Config Fields
```
uno logging config get-field LEVEL
uno logging config set-field LEVEL WARNING
```

### Restore Defaults
```
uno logging config restore-defaults
```

### Validate Logging Config
```
uno logging config validate
```

### Set Log Level
```
uno logging config set-level DEBUG
```

### Enable/Disable JSON Log Output
```
uno logging config set-json-format true
uno logging config set-json-format false
```

### Enable/Disable File Output
```
uno logging config set-file-output true --file-path=/tmp/uno.log
uno logging config set-file-output false
```

### Enable/Disable Console Output
```
uno logging config set-console-output true
uno logging config set-console-output false
```

---

## Advanced Usage
- The CLI is DI-compliant and can be scripted or extended for automation.
- See the CLI admin source for more: [`src/uno/cli/log_admin.py`](../../src/uno/cli/log_admin.py)

## Best Practices
- Use the CLI for live diagnostics and tuning in dev, test, and prod environments.
- Combine with structured logging and trace context for full observability.
