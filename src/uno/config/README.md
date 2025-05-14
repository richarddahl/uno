# Uno Configuration System

The Uno Configuration System provides a robust, flexible, and secure way to manage application configuration across different environments.

## Features

- **Type-safe Configuration**: Built on Pydantic for strong type checking and validation
- **Environment-based Configuration**: Support for development, testing, and production environments
- **Multiple Configuration Sources**: Load from .env files, environment variables, and code
- **Secure Configuration Values**: Protect sensitive configuration with masking, encryption, and access control
- **Key Rotation**: Utilities for securely rotating encryption keys
- **DI Integration**: Seamless integration with dependency injection system

## Quick Start

```python
from uno.config import UnoSettings, Environment, SecureField

class DatabaseSettings(UnoSettings):
    host: str = "localhost"
    port: int = 5432
    username: str = "postgres"
    password: str = SecureField(default="")
    
# Load settings
settings = await load_settings(DatabaseSettings, env=Environment.DEVELOPMENT)

# Access settings
print(f"Connecting to {settings.host}:{settings.port}")
print(f"Username: {settings.username}")
# Password is masked in logs automatically
print(f"Password: {settings.password}")  # Will show: Password: ******
```

## Documentation

For more detailed documentation, see:

- [User Guide](../../docs/config/user-guide.md) - For application developers using the configuration system
- [Developer Guide](../../docs/config/developer-guide.md) - For contributors extending the configuration system
- [Security Guide](../../docs/config/security-guide.md) - For understanding and implementing secure configuration

## License

MIT
