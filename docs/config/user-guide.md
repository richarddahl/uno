# Uno Configuration System - User Guide

This guide explains how to use the Uno Configuration System in your applications.

## Table of Contents

- [Basic Usage](#basic-usage)
- [Environment-Based Configuration](#environment-based-configuration)
- [Secure Configuration](#secure-configuration)
- [Loading Settings](#loading-settings)
- [Advanced Usage](#advanced-usage)

## Basic Usage

The Uno Configuration System is built on Pydantic to provide strong type checking and validation. To define your application's configuration, create a class that inherits from `UnoSettings`:

```python
from uno.config import UnoSettings

class AppSettings(UnoSettings):
    app_name: str = "My App"
    debug: bool = False
    log_level: str = "INFO"
    max_connections: int = 100
```

Then load and use your settings:

```python
from uno.config import load_settings

# Load settings
settings = await load_settings(AppSettings)

# Use settings
print(f"Starting {settings.app_name} with log level {settings.log_level}")
if settings.debug:
    print("Debug mode enabled")
```

## Environment-Based Configuration

Uno supports different environments (development, testing, production) with appropriate configuration for each.

### Setting the Environment

The environment is determined from environment variables in this order:

1. `UNO_ENV`
2. `ENVIRONMENT`
3. `ENV`

Values can be: `development`, `testing`, `production` (or shortened versions: `dev`, `test`, `prod`).

```bash
# Set environment
export UNO_ENV=development
```

### Environment Files

Uno loads configuration from multiple .env files in order:

1. `.env` - Base configuration for all environments
2. `.env.{environment}` - Environment-specific configuration
3. `.env.local` - Local development overrides (not loaded in production)

Example directory structure:

```
my_app/
  .env             # Base settings
  .env.development # Development-specific settings
  .env.testing     # Testing-specific settings
  .env.production  # Production-specific settings
  .env.local       # Local overrides (ignored in production)
```

Example `.env` file:

```
# Base configuration (.env)
APP_NAME=My App
DEBUG=false
LOG_LEVEL=INFO
```

Example `.env.development` file:

```
# Development configuration
DEBUG=true
LOG_LEVEL=DEBUG
```

## Secure Configuration

For sensitive configuration values (passwords, API keys, etc.), use the secure field utilities:

```python
from uno.config import UnoSettings, SecureField, SecureValueHandling

class ApiSettings(UnoSettings):
    api_url: str = "https://api.example.com"
    # Masked in logs, but stored in plaintext
    api_key: str = SecureField(default="", handling=SecureValueHandling.MASK)
    # Encrypted in storage, decrypted when accessed
    secret_key: str = SecureField(default="", handling=SecureValueHandling.ENCRYPT)
```

### Setting Up Encryption

Before using encrypted fields, you need to set up encryption:

```python
from uno.config import setup_secure_config

# Set up encryption with a master key
await setup_secure_config(
    master_key="your-very-secure-master-key",  # Or use UNO_MASTER_KEY env var
    key_version="v1"  # Version identifier for this key
)
```

In production, you should store the master key securely and provide it through environment variables:

```bash
export UNO_MASTER_KEY=your-very-secure-master-key
```

### Accessing Secure Values

Secure values are automatically masked in string representations:

```python
settings = await load_settings(ApiSettings)
print(f"API Key: {settings.api_key}")  # Prints: API Key: ******
```

To access the actual value:

```python
# Get the actual value
actual_key = settings.api_key.get_value()
```

## Loading Settings

Uno provides multiple ways to load settings:

### Basic Loading

```python
from uno.config import load_settings, Environment

# Load with default environment
settings = await load_settings(AppSettings)

# Load with specific environment
settings = await load_settings(AppSettings, env=Environment.TESTING)

# Load from specific directory
settings = await load_settings(AppSettings, config_path="/path/to/config")

# Load with overrides
settings = await load_settings(
    AppSettings,
    override_values={"debug": True, "log_level": "DEBUG"}
)
```

### Cached Configuration

For performance, use the cached `get_config` method:

```python
from uno.config import get_config

# First call loads and caches
settings = await get_config(AppSettings)

# Subsequent calls use the cache
settings_again = await get_config(AppSettings)  # Uses cached instance
```

### Dependency Injection Integration

Register your settings with the DI container:

```python
from uno.config import load_settings
from uno.config.di import ConfigRegistrationExtensions
from uno.di import Container

# Load settings
app_settings = await load_settings(AppSettings)

# Register with container
container = Container()
ConfigRegistrationExtensions.register_configuration(container, app_settings)

# Later, resolve from container
settings = container.resolve(AppSettings)
```

## Advanced Usage

### Component-Specific Settings

You can create specialized settings for different components:

```python
class DatabaseSettings(UnoSettings):
    host: str = "localhost"
    port: int = 5432
    username: str = "postgres"
    password: str = SecureField(default="")
    
class CacheSettings(UnoSettings):
    url: str = "redis://localhost:6379"
    timeout: int = 30
```

Uno will automatically look for component-specific .env files:

- `.env.database` for `DatabaseSettings`
- `.env.cache` for `CacheSettings`

### Environment Variable Mapping

Settings properties can be set from environment variables:

1. Exact match with field name: `host` -> `host`
2. Uppercase with underscores: `connectionString` -> `CONNECTION_STRING`
3. With env_prefix if defined: `host` -> `MYAPP_HOST`

### Type Handling for Environment Variables

Environment variables are automatically converted to the appropriate type:

```python
# .env file
MAX_CONNECTIONS=50
ENABLED=true
HOSTS=host1.example.com,host2.example.com
CONFIG={"key": "value"}
```

```python
class MySettings(UnoSettings):
    max_connections: int  # Converted to int
    enabled: bool  # Converted to bool
    hosts: list[str]  # Parsed as comma-separated list
    config: dict  # Parsed as JSON
```

### Key Rotation for Encrypted Values

If you need to rotate encryption keys:

```python
from uno.config import setup_secure_config
from uno.config.key_rotation import setup_key_rotation, rotate_secure_values

# Set up key rotation with old and new keys
await setup_key_rotation(
    old_key="old-master-key",
    new_key="new-master-key",
    old_version="v1",
    new_version="v2"
)

# Rotate encrypted values
secure_values = [settings.api_key, settings.secret_key]
await rotate_secure_values(secure_values, new_key_version="v2")
```
