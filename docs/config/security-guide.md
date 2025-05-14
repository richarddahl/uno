# Uno Configuration System - Security Guide

This guide explains the security features of the Uno Configuration System and how to use them effectively.

## Table of Contents

- [Security Overview](#security-overview)
- [Securing Sensitive Configuration](#securing-sensitive-configuration)
- [Encryption Setup](#encryption-setup)
- [Key Management](#key-management)
- [Access Control](#access-control)
- [Production Security Best Practices](#production-security-best-practices)
- [Security Considerations and Limitations](#security-considerations-and-limitations)

## Security Overview

The Uno Configuration System provides multiple layers of protection for sensitive configuration:

1. **Masking** - Hide sensitive values in logs and string representations
2. **Encryption** - Encrypt sensitive values at rest
3. **Access Control** - Control and audit access to sensitive values
4. **Memory Protection** - Best-effort protection of sensitive values in memory

## Securing Sensitive Configuration

### Using SecureField

The easiest way to secure sensitive configuration is using `SecureField`:

```python
from uno.config import UnoSettings, SecureField, SecureValueHandling

class DatabaseSettings(UnoSettings):
    host: str = "localhost"
    port: int = 5432
    username: str = "admin"
    
    # Masked in logs but stored as plaintext in memory
    password: str = SecureField(default="")
    
    # Encrypted at rest, decrypted when accessed
    api_key: str = SecureField(
        default="",
        handling=SecureValueHandling.ENCRYPT
    )
    
    # Always encrypted, even in memory (highest security)
    master_key: str = SecureField(
        default="",
        handling=SecureValueHandling.SEALED
    )
```

### Security Levels

Choose the appropriate security level for each sensitive value:

1. **MASK** - For low sensitivity values that should be hidden in logs
   - Values are plaintext in memory
   - Values are masked in logs and string representations
   - Minimal performance impact

2. **ENCRYPT** - For sensitive values that need protection at rest
   - Values are encrypted when stored
   - Values are decrypted automatically when accessed
   - Moderate performance impact

3. **SEALED** - For highly sensitive values requiring strict access control
   - Values are always encrypted, even in memory
   - Values require explicit decryption to access
   - Highest security level
   - Highest performance impact

## Encryption Setup

Before using encrypted fields, you must set up encryption:

```python
from uno.config import setup_secure_config

# Simple setup with a master key
await setup_secure_config(
    master_key="your-very-secure-master-key"
)

# Advanced setup with key version and salt file
await setup_secure_config(
    master_key="your-very-secure-master-key",
    salt_file="/path/to/salt.bin",
    key_version="v1"
)
```

### Using Environment Variables

In production, provide the master key through environment variables:

```bash
export UNO_MASTER_KEY=your-very-secure-master-key
export UNO_MASTER_SALT=your-custom-salt  # Optional
```

## Key Management

### Key Versioning

The system supports key versioning for smooth key rotation:

```python
from uno.config.secure import SecureValue

# Register multiple key versions
await SecureValue.setup_encryption(
    master_key="old-key",
    key_version="v1"
)

await SecureValue.setup_encryption(
    master_key="new-key",
    key_version="v2"
)

# Set the current key for new encryptions
await SecureValue.set_current_key_version("v2")
```

### Key Rotation

You can rotate keys for encrypted values:

```python
from uno.config.key_rotation import rotate_secure_values

# Collect secure values that need rotation
secure_values = [
    settings.api_key,
    settings.master_key,
    other_settings.secret_token
]

# Rotate to new key version
await rotate_secure_values(
    values=secure_values,
    new_key_version="v2",
    parallel=True
)
```

### Simplified Key Rotation

For a simpler approach:

```python
from uno.config.key_rotation import setup_key_rotation

# Set up with both old and new keys
await setup_key_rotation(
    old_key="old-master-key",
    new_key="new-master-key",
    old_version="v1",
    new_version="v2"
)
```

## Access Control

### Auditing Access

Use the `requires_secure_access` decorator to control and audit access to secure values:

```python
from uno.config.secure import requires_secure_access

@requires_secure_access
def get_database_credentials(settings: DatabaseSettings) -> tuple[str, str]:
    """Get database credentials."""
    # This access will be logged
    username = settings.username
    # This access will be logged with a warning for SEALED values
    password = settings.password.get_value()
    return username, password
```

### SEALED Values

For highest security, use SEALED values with explicit access:

```python
# Settings definition
class ApiSettings(UnoSettings):
    api_key: str = SecureField(default="", handling=SecureValueHandling.SEALED)

# Accessing sealed values
@requires_secure_access
def use_api_key(settings: ApiSettings) -> None:
    # Explicit decryption required
    with settings.api_key as key:  # Context manager handles cleanup
        actual_key = key.get_value()
        # Use the key...
    # Key is automatically cleared from memory after the block
```

## Production Security Best Practices

1. **Master Key Storage**:
   - Use a secure secret management service (AWS Secrets Manager, HashiCorp Vault, etc.)
   - Never store master keys in code or configuration files
   - Inject master keys through environment variables or secure file

2. **Environment Management**:
   - Ensure `.env.local` files are excluded from version control
   - Use strict file permissions for .env files
   - In production, prefer environment variables over .env files

3. **Key Rotation**:
   - Regularly rotate encryption keys (schedule depends on security requirements)
   - Have a recovery plan for key rotation failures
   - Test key rotation in staging environments first

4. **Access Control**:
   - Restrict access to sensitive configuration to only necessary components
   - Log and alert on unexpected access to sealed values
   - Consider implementing a timeout for decrypted values

5. **Monitoring and Auditing**:
   - Monitor logs for secure value access
   - Set up alerts for failed decryption attempts
   - Regularly audit sensitive value access patterns

## Security Considerations and Limitations

### Memory Protection Limitations

Python's garbage collection and string immutability present challenges for memory security:

- The system uses best-effort techniques to clear sensitive data from memory
- Data might remain in memory temporarily due to Python's memory management
- String immutability means copies might exist in memory

### Encryption Strength

The default encryption uses:

- Fernet symmetric encryption (AES-128 in CBC mode with PKCS7 padding)
- PBKDF2HMAC with SHA-256 for key derivation
- 200,000 iterations for key derivation (configurable)

For extremely sensitive applications, consider:

- Increasing KDF iterations (trade-off with performance)
- Using custom secure value implementations with hardware security modules
- Implementing additional access controls outside the configuration system

### Source Code Protection

The Uno Configuration System protects values at runtime, but consider:

- Source code might contain default sensitive values
- Git history might contain sensitive values from previous commits
- Pre-commit hooks to detect and prevent committing sensitive values

### Secure Development Workflow

1. **Development**: Use fake/mock secrets in development environments
2. **Testing**: Use dedicated test credentials with limited permissions
3. **Staging**: Use production-like secrets with the same rotation policies
4. **Production**: Use full security measures with restricted access
