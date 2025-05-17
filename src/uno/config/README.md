# Uno Configuration System

The Uno configuration system provides tools for loading and managing configuration from various sources including environment variables and files.

## Key Features

- Environment-aware configuration loading
- Secure value handling with encryption
- Environment variable caching for performance
- Configuration file support (.env files)
- Configuration manager for easy DI integration

## Migration Notice: Schema Validation

The schema validation functionality previously provided by this package has been moved to the dedicated `uno.ui.schema` package. This provides a cleaner separation of concerns and allows the UI schema system to evolve independently.

### Migration Guide

If you were using schema validation features like:

```python
from uno.config import (
    SchemaVersion,
    ValidationLevel,
    ValidationScope,
    FieldCategory,
    FieldDisplayType,
    ConfigField,
    EnhancedConfig,
    fields_dependency,
    generate_markdown_docs,
    export_schema_json,
    requires,
)
```

You should now import these from the `uno.ui.schema` package:

```python
from uno.ui.schema import (
    SchemaVersion,
    ValidationLevel, 
    ValidationScope,
    FieldCategory,
    FieldDisplayType,
    discover_config_classes,
    SchemaExtensionRegistry,
    SchemaAdapter,
)

# Additional components are available in specific modules:
from uno.ui.schema.components import UIComponentRegistry
from uno.ui.schema.registry import (
    SchemaRegistry,
    register_discovered_schemas,
    create_api_response,
)
```

The new package offers an improved and more extensible API for schema-driven UI generation with support for various UI frameworks.
