# Enhanced Configuration Schema Validation

The Uno framework provides a robust schema validation system for configuration objects, extending Pydantic's capabilities with additional features designed for enterprise applications.

## Key Features

- **Schema Versioning**: Track and manage configuration schema changes
- **Enhanced Validation**: Add format patterns, cross-field validation rules
- **Environment-Specific Validation**: Different validation rules by environment
- **Documentation Generation**: Auto-generate documentation from schema definitions
- **Validation Levels**: Control validation strictness as needed

## Basic Usage

### Creating an Enhanced Configuration Class

```python
from uno.config import EnhancedConfig, ConfigField, SchemaVersion, ValidationScope

class DatabaseConfig(EnhancedConfig):
    """Database connection configuration."""
    
    # Define schema version to track changes
    schema_version = SchemaVersion(1, 0, 0)
    
    # Basic fields with metadata
    host: str = ConfigField(
        description="Database host address",
        example="db.example.com"
    )
    
    port: int = ConfigField(
        default=5432,
        description="Database port number",
        example=5432
    )
    
    username: str = ConfigField(
        description="Database username",
        example="app_user"
    )
    
    password: str = ConfigField(
        description="Database password",
        format_pattern=r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$"
    )
    
    debug_mode: bool = ConfigField(
        default=False,
        description="Enable debug logging for database queries",
        required_in=ValidationScope.DEVELOPMENT
    )
```

### Using the Configuration

```python
# Load with standard validation (default)
db_config = DatabaseConfig(
    host="localhost",
    port=5432,
    username="app_user",
    password="Secure123"
)

# Access fields normally
connection_string = f"postgresql://{db_config.username}:{db_config.password}@{db_config.host}:{db_config.port}/mydb"
```

## Advanced Features

### Validation Levels

Control how strictly validation is enforced:

```python
from uno.config import ValidationLevel

# Use basic validation (type checking only)
config = DatabaseConfig(
    host="localhost",
    username="app_user",
    password="weak",  # Would fail format validation, but skipped in BASIC mode
    validation_level=ValidationLevel.BASIC
)

# Available validation levels:
# - ValidationLevel.NONE: No validation (unsafe)
# - ValidationLevel.BASIC: Type validation only
# - ValidationLevel.STANDARD: Type + field-level validations (default)
# - ValidationLevel.STRICT: All validations including cross-field
```

### Cross-Field Validation

Validate relationships between fields:

```python
from uno.config import EnhancedConfig, ConfigField, requires, fields_dependency

@requires(
    lambda config: 0 < config.min_connections <= config.max_connections, 
    "Min connections must be positive and not exceed max connections"
)
@fields_dependency(
    field="connection_timeout", 
    depends_on="enable_timeout",
    error_message="connection_timeout requires enable_timeout=True"
)
class ConnectionPoolConfig(EnhancedConfig):
    """Connection pool configuration."""
    
    min_connections: int = ConfigField(default=1)
    max_connections: int = ConfigField(default=10)
    enable_timeout: bool = ConfigField(default=False)
    connection_timeout: int | None = ConfigField(default=None)
```

### Versioned Configuration Fields

Track when fields were added or deprecated:

```python
class ApiConfig(EnhancedConfig):
    """API configuration with versioned fields."""
    
    # Current schema version
    schema_version = SchemaVersion(2, 1, 0)
    
    # Original field from v1.0
    endpoint: str = ConfigField(
        description="API endpoint URL",
        min_version=SchemaVersion(1, 0, 0)
    )
    
    # Added in v1.5
    timeout: int = ConfigField(
        default=30,
        description="Request timeout in seconds",
        min_version=SchemaVersion(1, 5, 0)
    )
    
    # Added in v2.0
    use_https: bool = ConfigField(
        default=True,
        description="Use HTTPS instead of HTTP",
        min_version=SchemaVersion(2, 0, 0)
    )
    
    # Deprecated in v2.1
    legacy_format: str = ConfigField(
        default="json",
        description="Response format (deprecated, use 'format' instead)",
        min_version=SchemaVersion(1, 0, 0),
        max_version=SchemaVersion(2, 1, 0),
        deprecated=True
    )
    
    # Replacement for legacy_format
    format: str = ConfigField(
        default="json",
        description="Response format (json, xml, etc.)",
        min_version=SchemaVersion(2, 0, 0)
    )
```

## Documentation Generation

Generate documentation for your configuration schemas:

```python
from uno.config import export_schema_json, generate_markdown_docs, discover_config_classes

# Export as JSON schema
schema_json = export_schema_json(DatabaseConfig)
with open("db_config_schema.json", "w") as f:
    f.write(schema_json)

# Generate Markdown documentation
docs = generate_markdown_docs([DatabaseConfig, ApiConfig], output_dir="./docs")

# Discover all config classes in a module and document them
import my_app.config
configs = discover_config_classes(my_app.config)
generate_markdown_docs(configs, output_dir="./docs")
```

## Environment-Specific Validation

```python
from uno.config import Environment

# Validate for a specific environment
errors = config.validate_for_environment(Environment.PRODUCTION)
if errors:
    print("Configuration is not valid for production:")
    for error in errors:
        print(f"- {error}")
```

## Best Practices

1. **Schema Versioning**: Always set a proper `schema_version` and increment it according to semantic versioning principles:
   - Major version: Breaking changes
   - Minor version: Non-breaking additions
   - Patch version: Documentation/description changes

2. **Field Documentation**: Always provide clear descriptions and examples for configuration fields.

3. **Validation Strategy**: Choose appropriate validation levels for different contexts:
   - Use `STANDARD` for normal operation
   - Consider `STRICT` for critical systems
   - Use `BASIC` only when performance is critical
   - Avoid `NONE` except in special cases

4. **Environment Awareness**: Use `required_in` to specify which environments require certain fields.

5. **Cross-Field Validation**: Use `@requires` and `@fields_dependency` to enforce relationships between fields.

6. **Documentation Generation**: Regularly update and publish your configuration documentation.
