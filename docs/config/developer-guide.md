# Uno Configuration System - Developer Guide

This guide explains the architecture of the Uno Configuration System and how to extend it.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Core Components](#core-components)
- [Extending the System](#extending-the-system)
- [Security Implementation](#security-implementation)
- [Best Practices](#best-practices)
- [Testing](#testing)

## Architecture Overview

The Uno Configuration System is designed with the following principles:

1. **Type safety** - Strongly typed configuration using Pydantic
2. **Environment awareness** - Different configurations for different environments
3. **Secure by default** - Built-in security for sensitive configuration values
4. **Extensibility** - Easy to extend for custom needs
5. **Async-first** - Designed for async/await usage throughout

### Key Design Decisions

- Uses Pydantic V2 for validation and typing
- Follows Python 3.13 typing conventions
- Implements async-first approach with coroutines
- Prioritizes security with dedicated secure value handling

## Core Components

The configuration system consists of several key components:

### Environment Management (`base.py`)

The `Environment` enum represents different runtime environments:

```python
class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"
```

### Base Settings Class (`base.py`)

`UnoSettings` extends Pydantic's `BaseSettings` to provide:

- Environment-specific configuration loading
- Secure field handling
- Type conversion

### Settings Loading (`settings.py`)

Functions for loading settings from various sources:

- `load_settings()` - Load settings with explicit control
- `get_config()` - Cached configuration loading

### Environment Variable Loading (`env_loader.py`)

Utilities for loading environment variables:

- `load_env_files()` - Load from multiple .env files with proper cascading
- `get_env_value()` - Get a value with proper fallbacks

### Secure Configuration (`secure.py`)

Classes for handling sensitive configuration:

- `SecureValue` - Container for secure values with controlled access
- `SecureValueHandling` - Enum for different security strategies (mask, encrypt, seal)
- `SecureField` - Factory function for secure Pydantic fields

### Key Rotation (`key_rotation.py`)

Utilities for rotating encryption keys:

- `rotate_secure_values()` - Rotate keys for multiple values
- `setup_key_rotation()` - Set up key rotation infrastructure

### Error Handling (`errors.py`)

Specialized error classes for configuration issues:

- `ConfigError` - Base class for all configuration errors
- `ConfigValidationError`, `ConfigFileNotFoundError`, etc.

### DI Integration (`di.py`)

Integration with the dependency injection system:

- `ConfigRegistrationExtensions` - Register configuration with DI container

## Extending the System

### Creating Custom Settings Loaders

You can create custom settings loaders by extending the base functionality:

```python
async def load_from_database(
    settings_class: type[T],
    connection_string: str,
    env: Environment | None = None
) -> T:
    """Load settings from a database."""
    if env is None:
        env = Environment.get_current()
        
    # Load base settings first
    settings = await load_settings(settings_class, env=env)
    
    # Connect to database and override settings
    # ... (database-specific code)
    
    return settings
```

### Implementing Custom Secure Value Handling

You can implement custom secure value handling by extending `SecureValue`:

```python
class VaultSecureValue(SecureValue[T]):
    """SecureValue implementation that uses HashiCorp Vault."""
    
    _vault_client = None
    
    @classmethod
    async def setup_vault(cls, vault_url: str, token: str):
        """Set up the Vault client."""
        # ... (vault client setup)
        
    def _encrypt(self, key_version: str | None = None) -> None:
        """Encrypt using Vault."""
        # ... (vault encryption implementation)
        
    def _decrypt(self) -> str:
        """Decrypt using Vault."""
        # ... (vault decryption implementation)
```

### Custom Field Types

You can create custom field types for specific needs:

```python
def ConnectionStringField(
    default: str = ...,
    *,
    handling: SecureValueHandling = SecureValueHandling.ENCRYPT,
    **kwargs
) -> Any:
    """Field for database connection strings with validation."""
    field = SecureField(default, handling=handling, **kwargs)
    
    # Add connection string validation
    validators = kwargs.get("validators", [])
    validators.append(validate_connection_string)
    field.validators = validators
    
    return field
```

## Security Implementation

### Secure Value Handling

The `SecureValue` class provides three levels of security:

1. **MASK** - Values are shown as masked (`******`) in logs and string representations but kept as plaintext in memory
2. **ENCRYPT** - Values are encrypted at rest and decrypted when accessed
3. **SEALED** - Values are always encrypted, even in memory, and require explicit decryption

### Key Management

Encryption keys are managed with:

- Key versioning
- Key derivation functions (KDF) for secure key generation
- Support for key rotation

### Memory Security

The system implements best-effort memory security:

- Overwriting sensitive data in memory when no longer needed
- Context manager support for automatic cleanup
- Protection against serialization and introspection

### Implementation Details

Encryption uses:

- Fernet symmetric encryption
- PBKDF2HMAC for key derivation
- SHA-256 for hashing
- Constant-time comparisons for equality checks

## Best Practices

### Code Organization

- Create specialized settings classes for different components
- Place component-specific settings in their own modules
- Use consistent naming: `{Component}Settings`

### Type Definitions

- Use Python 3.13 type hints with primitives (`dict`, not `Dict`, etc.)
- Use `X | None` instead of `Optional[X]`
- Define complex types with `TypeAdapter` for validation

### Security Practices

- Never store master keys in code
- Use environment variables for master keys in production
- Rotate keys periodically
- Use `ENCRYPT` handling for truly sensitive information

### Settings Design

- Provide sensible defaults
- Document each setting with docstrings
- Group related settings in nested models
- Use enums for settings with a fixed set of values

## Testing

### Testing Configuration Loading

```python
import pytest
from uno.config import load_settings, Environment

@pytest.mark.asyncio
async def test_load_settings():
    # Create temporary .env file for testing
    with open(".env.test", "w") as f:
        f.write("APP_NAME=Test App\n")
        f.write("DEBUG=true\n")
    
    # Load settings
    settings = await load_settings(AppSettings, env=Environment.TESTING)
    
    # Verify settings
    assert settings.app_name == "Test App"
    assert settings.debug == True
```

### Testing Secure Values

```python
import pytest
from uno.config import SecureValue, SecureValueHandling, setup_secure_config

@pytest.mark.asyncio
async def test_secure_value_encryption():
    # Set up encryption for testing
    await setup_secure_config(master_key="test-key")
    
    # Create secure value
    value = SecureValue("secret", handling=SecureValueHandling.ENCRYPT)
    
    # Test encryption
    assert str(value) == "******"  # Masked in string representation
    assert value.get_value() == "secret"  # Can get actual value
```

### Mocking Configuration

```python
import pytest
from unittest.mock import patch
from uno.config import get_config

@pytest.mark.asyncio
async def test_with_mocked_config():
    # Create mock settings
    mock_settings = AppSettings(app_name="Mocked App", debug=True)
    
    # Patch the config cache
    with patch("uno.config.settings._config_cache", {AppSettings: mock_settings}):
        # Get config (should return our mock)
        settings = await get_config(AppSettings)
        
        # Verify mock is used
        assert settings.app_name == "Mocked App"
```
