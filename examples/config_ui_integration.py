"""Example demonstrating configuration UI integration capabilities.

This example shows how to create configuration schemas with UI metadata
and expose them through API endpoints that can be consumed by UI tools.
"""

import json
from enum import Enum
from pathlib import Path
from typing import Any

from uno.config import (
    ConfigField,
    ConfigSchemaRegistry,
    EnhancedConfig,
    FieldCategory,
    FieldDisplayType,
    SchemaVersion,
    ValidationScope,
    create_api_response,
    register_discovered_schemas,
)


class LogFormat(str, Enum):
    """Supported log formats."""

    TEXT = "text"
    JSON = "json"
    XML = "xml"


class LogLevel(str, Enum):
    """Log levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class DatabaseLoggingConfig(EnhancedConfig):
    """Database logging configuration example with UI metadata."""

    # Class-level schema metadata for UI
    schema_meta = {
        "title": "Database Logging",
        "description": "Configuration for database logging and monitoring",
        "icon": "database",
        "category": "logging",
        "tags": ["database", "logging", "monitoring"],
    }

    # Schema version
    schema_version = SchemaVersion(1, 0, 0)

    # General settings
    enabled: bool = ConfigField(
        default=True,
        description="Enable database logging",
        display_name="Enable Logging",
        display_type=FieldDisplayType.CHECKBOX,
        category=FieldCategory.GENERAL,
        order=1,
    )

    level: LogLevel = ConfigField(
        default=LogLevel.INFO,
        description="Minimum log level to record",
        display_name="Log Level",
        display_type=FieldDisplayType.SELECT,
        options=["debug", "info", "warning", "error"],
        category=FieldCategory.GENERAL,
        order=2,
        depends_on_field="enabled",
        depends_on_value=True,
    )

    # Format settings
    format: LogFormat = ConfigField(
        default=LogFormat.TEXT,
        description="Log output format",
        display_name="Log Format",
        display_type=FieldDisplayType.RADIO,
        options=["text", "json", "xml"],
        category=FieldCategory.GENERAL,
        order=3,
        depends_on_field="enabled",
        depends_on_value=True,
    )

    # Advanced settings
    max_file_size_mb: int = ConfigField(
        default=10,
        description="Maximum log file size in megabytes",
        display_name="Max File Size (MB)",
        display_type=FieldDisplayType.NUMBER,
        category=FieldCategory.ADVANCED,
        visibility="advanced",
        order=1,
    )

    retention_days: int = ConfigField(
        default=30,
        description="Number of days to retain logs",
        display_name="Retention Period (days)",
        display_type=FieldDisplayType.SLIDER,
        category=FieldCategory.ADVANCED,
        visibility="advanced",
        order=2,
    )

    # Security settings
    include_sensitive_data: bool = ConfigField(
        default=False,
        description="Include sensitive data in logs (not recommended for production)",
        display_name="Include Sensitive Data",
        display_type=FieldDisplayType.CHECKBOX,
        category=FieldCategory.SECURITY,
        help_text="WARNING: Enabling this option may expose sensitive information in logs.",
        required_in=ValidationScope.DEVELOPMENT,
        order=1,
    )


class ApiKeyConfig(EnhancedConfig):
    """API key configuration example with UI metadata."""

    # Class-level schema metadata for UI
    schema_meta = {
        "title": "API Authentication",
        "description": "API key authentication settings",
        "icon": "key",
        "category": "security",
        "tags": ["api", "security", "authentication"],
    }

    # Schema version
    schema_version = SchemaVersion(1, 1, 0)

    # API Key settings
    api_key: str = ConfigField(
        description="API key for authentication",
        display_name="API Key",
        display_type=FieldDisplayType.PASSWORD,
        format_pattern=r"^[A-Za-z0-9]{32}$",
        category=FieldCategory.SECURITY,
        placeholder="Enter 32-character API key",
        help_text="A 32-character hexadecimal API key used for authentication",
        order=1,
    )

    # Usage settings
    rate_limit: int = ConfigField(
        default=100,
        description="Maximum API calls per minute",
        display_name="Rate Limit",
        display_type=FieldDisplayType.NUMBER,
        category=FieldCategory.PERFORMANCE,
        order=1,
    )

    expiration_days: int = ConfigField(
        default=90,
        description="Number of days until API key expires",
        display_name="Expiration Period",
        display_type=FieldDisplayType.NUMBER,
        category=FieldCategory.SECURITY,
        help_text="Set to 0 for no expiration (not recommended)",
        order=2,
    )


async def main() -> None:
    """Run the example."""
    print("Registering configuration schemas...")

    # Register schemas manually
    ConfigSchemaRegistry.register(DatabaseLoggingConfig)
    ConfigSchemaRegistry.register(ApiKeyConfig)

    # List registered schemas
    schemas = ConfigSchemaRegistry.list_schemas()
    print(f"Found {len(schemas)} registered schemas:")
    for schema in schemas:
        print(f"  - {schema['title']} (v{schema['version']}): {schema['category']}")

    # Create API response for a schema
    print("\nGenerating API response for DatabaseLoggingConfig...")
    api_response = create_api_response(DatabaseLoggingConfig)

    # Save as JSON for UI consumption
    output_dir = Path.cwd()
    output_file = output_dir / "db_logging_schema.json"

    with open(output_file, "w") as f:
        json.dump(api_response, f, indent=2)

    print(f"Saved API response to {output_file}")

    # Show how to use the API response
    print("\nExample API endpoints for UI integration:")
    print("GET /api/config/schemas - List all available schemas")
    print("GET /api/config/schemas/{schema_id} - Get schema details")
    print("GET /api/config/instances/{schema_id} - Get configured instances")
    print("POST /api/config/instances/{schema_id} - Create configuration instance")
    print("PUT /api/config/instances/{schema_id}/{instance_id} - Update configuration")

    # Example JSON Schema structure
    print("\nGenerated UI-compatible JSON Schema:")
    json_schema = DatabaseLoggingConfig.to_json_schema()
    print(json.dumps(json_schema["schema"]["properties"]["level"], indent=2))


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
