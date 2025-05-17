# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""Example using the enhanced schema validation features."""

from enum import Enum
from pathlib import Path

from uno.config import (
    ConfigField,
    EnhancedConfig,
    Environment,
    SchemaVersion,
    ValidationLevel,
    ValidationScope,
    export_schema_json,
    fields_dependency,
    generate_markdown_docs,
    requires,
)


class LogLevel(str, Enum):
    """Log levels for application."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DatabaseType(str, Enum):
    """Supported database types."""

    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"


@requires(
    lambda c: not (
        c.database_type == DatabaseType.SQLITE and c.connection_pool_size > 1
    ),
    "SQLite does not support connection pools larger than 1",
)
@fields_dependency(
    field="connection_pool_size",
    depends_on="use_connection_pooling",
    error_message="connection_pool_size requires use_connection_pooling=True",
)
class AppConfig(EnhancedConfig):
    """Application configuration with enhanced schema validation."""

    # Schema version for this configuration
    schema_version = SchemaVersion(1, 2, 0)

    # Application settings
    app_name: str = ConfigField(
        description="Application name",
        example="My Awesome App",
    )

    log_level: LogLevel = ConfigField(
        default=LogLevel.INFO,
        description="Application log level",
    )

    debug_mode: bool = ConfigField(
        default=False,
        description="Enable debug mode",
        required_in=ValidationScope.DEVELOPMENT,
    )

    # Database settings
    database_type: DatabaseType = ConfigField(
        default=DatabaseType.POSTGRESQL,
        description="Type of database to use",
    )

    database_host: str = ConfigField(
        default="localhost",
        description="Database host address",
        format_pattern=r"^[a-zA-Z0-9.-]+$",
        example="db.example.com",
    )

    database_port: int = ConfigField(
        default=5432,
        description="Database port number",
    )

    use_connection_pooling: bool = ConfigField(
        default=True,
        description="Whether to use connection pooling",
        min_version=SchemaVersion(1, 1, 0),
    )

    connection_pool_size: int = ConfigField(
        default=5,
        description="Size of the connection pool",
        min_version=SchemaVersion(1, 1, 0),
    )

    # API settings
    api_rate_limit: int = ConfigField(
        default=100,
        description="API rate limit per minute",
    )

    api_timeout: int = ConfigField(
        default=30,
        description="API timeout in seconds",
    )

    # Deprecated field
    legacy_cache_mode: str = ConfigField(
        default="memory",
        description="Legacy cache mode (deprecated)",
        deprecated=True,
        min_version=SchemaVersion(1, 0, 0),
        max_version=SchemaVersion(1, 2, 0),
    )


def main() -> None:
    """Run the example."""
    # Create a valid configuration
    config = AppConfig(
        app_name="Schema Example",
        database_host="localhost",
        use_connection_pooling=True,
        connection_pool_size=10,
    )

    print(f"Created configuration: {config.app_name}")
    print(
        f"Database: {config.database_type.value} at {config.database_host}:{config.database_port}"
    )
    print(
        f"Connection pool: {config.connection_pool_size if config.use_connection_pooling else 'Disabled'}"
    )

    # Generate schema documentation
    print("\nGenerating schema documentation...")
    schema_json = export_schema_json(AppConfig)
    print(f"Schema JSON: {len(schema_json)} bytes")

    # Export to current directory
    docs_dir = Path.cwd()
    generate_markdown_docs([AppConfig], output_dir=docs_dir)
    print(f"Markdown documentation generated to: {docs_dir}/AppConfig.md")

    # Validate for specific environment
    print("\nValidating for production environment...")
    errors = config.validate_for_environment(Environment.PRODUCTION)
    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("Configuration is valid for production")

    # Demonstrate validation levels
    try:
        # This would normally fail validation because SQLite does not support connection pools > 1
        print("\nTrying invalid configuration with STANDARD validation...")
        invalid_config = AppConfig(
            app_name="Invalid Config",
            database_type=DatabaseType.SQLITE,
            use_connection_pooling=True,
            connection_pool_size=5,
            validation_level=ValidationLevel.STANDARD,
        )
        print("This should not be reached!")
    except Exception as e:
        print(f"Validation error (expected): {e}")

    # But with BASIC validation, cross-field validation is skipped
    print("\nTrying invalid configuration with BASIC validation...")
    invalid_config = AppConfig(
        app_name="Invalid Config",
        database_type=DatabaseType.SQLITE,
        use_connection_pooling=True,
        connection_pool_size=5,
        validation_level=ValidationLevel.BASIC,
    )
    print(
        "Configuration created with BASIC validation (cross-field validation skipped)"
    )
    print(f"Database type: {invalid_config.database_type.value}")
    print(f"Connection pool size: {invalid_config.connection_pool_size}")


if __name__ == "__main__":
    main()
