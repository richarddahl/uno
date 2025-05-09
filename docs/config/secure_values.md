# Secure Configuration Value Handling

This document describes the secure value handling capabilities in the Uno framework's configuration system.

## Overview

The secure configuration value handling system allows you to:

1. **Mask sensitive values** in logs, error messages, and serialized output
2. **Encrypt sensitive values** in memory or storage
3. **Control access** to secure values through dependency injection
4. **Audit access** to sensitive configuration

## Configuration Types

The system supports three types of secure value handling:

- **Mask**: Values are stored in plaintext but are masked in logs and string representations
- **Encrypt**: Values are encrypted in storage but decrypted when accessed in memory
- **Sealed**: Values are always encrypted and require special handling to access

## Basic Usage

### Defining Secure Configuration

```python
from uno.config import SecureField, SecureValueHandling, UnoSettings

class DatabaseConfig(UnoSettings):
    host: str = "localhost"
    port: int = 5432
    username: str = "db_user"
    
    # Simple masking - value is in plaintext but masked in logs
    password: str = SecureField("default_password")
    
    # Encrypted value - requires master key
    api_key: str = SecureField(
        "default-api-key", 
        handling=SecureValueHandling.ENCRYPT
    )
    
    # Sealed value - cannot be accessed directly
    encryption_key: str = SecureField(
        "default-encryption-key",
        handling=SecureValueHandling.SEALED
    )
```

### Setting Up Encryption

For encrypted and sealed values, you must set up encryption with a master key:

```python
from uno.config import setup_secure_config

# Option 1: Pass the master key directly
setup_secure_config("your-master-key")

# Option 2: Set via environment variable
# export UNO_MASTER_KEY=your-master-key
setup_secure_config()  # Will use UNO_MASTER_KEY
```

### Accessing Secure Values

```python
# Create config instance
config = DatabaseConfig()

# Access non-secure values normally
host = config.host  # "localhost"

# Access masked values
password_secure = config.password  # SecureValue instance
password_value = config.password.get_value()  # "default_password"

# Access encrypted values (requires setup_secure_config)
api_key_value = config.api_key.get_value()  # "default-api-key"

# Sealed values will raise an exception when accessed directly
try:
    encryption_key = config.encryption_key.get_value()
except Exception as e:
    print(f"Cannot access sealed value: {e}")
```

## Dependency Injection Integration

For proper secure value handling in services, use dependency injection with the `ConfigProvider`:

### Registering Secure Configuration

```python
from uno.config.di import register_secure_config
from uno.di import Container

# Create container
container = Container()

# Register secure config
register_secure_config(container, DatabaseConfig)
```

### Service Consumption

```python
from uno.config.di import ConfigProviderProtocol, ConfigProvider
from typing import Protocol

class DatabaseConfigProtocol(Protocol):
    host: str
    port: int
    username: str
    # Note: Don't include secure fields in protocol

class DatabaseService:
    def __init__(self, config_provider: ConfigProvider[DatabaseConfig]):
        self.config = config_provider.get_settings()
        
        # Access regular values directly
        self.host = self.config.host
        self.port = self.config.port
        self.username = self.config.username
        
        # Access secure values through provider (logs access)
        self.password = config_provider.get_secure_value("password")
        self.api_key = config_provider.get_secure_value("api_key")
        
        # Note: Sealed values still can't be accessed directly
        # Must use special handling for sealed values
```

## Environment Variable Loading

Secure values can be loaded from environment variables just like regular configuration:

```bash
# Set secure values in environment
export DATABASE_PASSWORD=production-password
export DATABASE_API_KEY=production-api-key
export DATABASE_ENCRYPTION_KEY=production-encryption-key
```

The values will be automatically wrapped in SecureValue containers with the appropriate handling.

## Security Recommendations

1. **Never log secure values directly** - use the provided mechanisms
2. **Store master keys in secure storage** or environment variables, not in code
3. **Use SEALED handling** for the most sensitive data that should rarely be accessed
4. **Clear sensitive data** from memory when no longer needed
5. **Always access secure values** through the `ConfigProvider` in production code

## Advanced Usage: Custom Value Processors

For advanced scenarios where you need custom handling of secure values, you can implement
custom middleware through the DI system:

```python
@container.middleware(ConfigProvider)
def log_secure_config_access(provider: ConfigProvider, next: Callable):
    # Custom middleware to log all config access
    logger = container.resolve(Logger)
    logger.info(f"Config access: {provider.__class__.__name__}")
    return next(provider)
```
