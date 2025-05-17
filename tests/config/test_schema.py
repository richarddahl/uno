# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""Tests for the schema validation features."""

import asyncio
import json
import os
import re
import tempfile
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar, List

import pytest
from pydantic import ValidationError

from uno.config import (
    Config,
    ConfigField,
    EnhancedConfig,
    Environment,
    SchemaVersion,
    ValidationLevel,
    ValidationScope,
    discover_config_classes,
    export_schema_json,
    fields_dependency,
    generate_markdown_docs,
    requires,
)


class TestSchemaVersion:
    """Tests for SchemaVersion class."""

    def test_schema_version_creation(self) -> None:
        """Test that SchemaVersion can be created with valid values."""
        version = SchemaVersion(1, 2, 3)
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert str(version) == "1.2.3"

    def test_schema_version_compatibility(self) -> None:
        """Test version compatibility checking."""
        v1_0_0 = SchemaVersion(1, 0, 0)
        v1_1_0 = SchemaVersion(1, 1, 0)
        v1_2_0 = SchemaVersion(1, 2, 0)
        v2_0_0 = SchemaVersion(2, 0, 0)

        # Same major, higher minor is compatible
        assert v1_2_0.is_compatible_with(v1_0_0)
        assert v1_2_0.is_compatible_with(v1_1_0)
        assert v1_1_0.is_compatible_with(v1_0_0)

        # Same major, lower minor is not compatible
        assert not v1_0_0.is_compatible_with(v1_1_0)
        assert not v1_1_0.is_compatible_with(v1_2_0)

        # Different major is not compatible
        assert not v1_0_0.is_compatible_with(v2_0_0)
        assert not v2_0_0.is_compatible_with(v1_0_0)

        # Same version is always compatible
        assert v1_0_0.is_compatible_with(v1_0_0)
        assert v1_1_0.is_compatible_with(v1_1_0)
        assert v2_0_0.is_compatible_with(v2_0_0)

        # Patch version doesn't affect compatibility
        v1_0_1 = SchemaVersion(1, 0, 1)
        assert v1_0_1.is_compatible_with(v1_0_0)
        assert v1_0_0.is_compatible_with(v1_0_1)


class Status(str, Enum):
    """Test enum for configuration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class SimpleTestConfig(EnhancedConfig):
    """Simple test configuration with basic validation."""

    schema_version = SchemaVersion(1, 0, 0)

    name: str = ConfigField(
        description="The name of the application",
        example="My App",
    )
    timeout: int = ConfigField(
        default=30,
        description="Timeout in seconds",
        example=60,
    )
    api_key: str = ConfigField(
        description="API key for authentication",
        format_pattern=r"^[A-Za-z0-9]{32}$",
        example="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
    )
    status: Status = ConfigField(
        default=Status.INACTIVE,
        description="Current status of the application",
    )
    debug: bool = ConfigField(
        default=False,
        description="Enable debug mode",
        required_in=ValidationScope.DEVELOPMENT,
    )


class VersionedConfig(EnhancedConfig):
    """Test configuration with versioned fields."""

    schema_version = SchemaVersion(2, 1, 0)

    # Original fields in v1.0
    name: str = ConfigField(
        description="Service name",
        min_version=SchemaVersion(1, 0, 0),
    )

    # Added in v1.5
    timeout: int = ConfigField(
        default=60,
        description="Timeout in seconds",
        min_version=SchemaVersion(1, 5, 0),
    )

    # Added in v2.0
    api_version: str = ConfigField(
        default="v1",
        description="API version to use",
        min_version=SchemaVersion(2, 0, 0),
    )

    # Deprecated in v2.1
    legacy_mode: bool = ConfigField(
        default=False,
        description="Use legacy mode (deprecated)",
        min_version=SchemaVersion(1, 0, 0),
        max_version=SchemaVersion(2, 1, 0),
        deprecated=True,
    )


@requires(
    lambda config: config.min_conn <= config.max_conn,
    "Minimum connections must be less than or equal to maximum connections",
)
@fields_dependency(
    field="retry_interval",
    depends_on="enable_retry",
    error_message="retry_interval requires enable_retry to be set to True",
)
class ValidatedConfig(EnhancedConfig):
    """Test configuration with cross-field validation."""

    schema_version = SchemaVersion(1, 0, 0)

    # Connection settings
    min_conn: int = ConfigField(
        default=1,
        description="Minimum connections",
    )
    max_conn: int = ConfigField(
        default=10,
        description="Maximum connections",
    )

    # Retry settings
    enable_retry: bool = ConfigField(
        default=False,
        description="Enable retry mechanism",
    )
    retry_interval: int | None = ConfigField(
        default=None,
        description="Retry interval in seconds",
    )

    # Format validation
    email: str | None = ConfigField(
        default=None,
        description="Notification email",
        format_pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
    )


class TestEnhancedConfig:
    """Tests for EnhancedConfig class."""

    def test_field_descriptions(self) -> None:
        """Test that field descriptions are properly applied."""
        schema_info = SimpleTestConfig.get_schema_info()

        assert (
            schema_info["fields"]["name"]["description"]
            == "The name of the application"
        )
        assert schema_info["fields"]["timeout"]["description"] == "Timeout in seconds"
        assert (
            schema_info["fields"]["api_key"]["description"]
            == "API key for authentication"
        )

    def test_examples(self) -> None:
        """Test that examples are properly stored."""
        schema_info = SimpleTestConfig.get_schema_info()

        assert schema_info["fields"]["name"]["example"] == "My App"
        assert schema_info["fields"]["timeout"]["example"] == 60
        assert (
            schema_info["fields"]["api_key"]["example"]
            == "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
        )

    def test_format_pattern_validation(self) -> None:
        """Test format pattern validation."""
        # Valid API key
        config = SimpleTestConfig(
            name="Test App", api_key="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
        )
        assert config.api_key == "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"

        # Invalid API key
        with pytest.raises(ValidationError):
            SimpleTestConfig(name="Test App", api_key="invalid-key")

    def test_validation_level(self) -> None:
        """Test different validation levels."""
        # Standard validation (default)
        with pytest.raises(ValidationError):
            SimpleTestConfig(name="Test App", api_key="invalid-key")

        # Basic validation - should skip format pattern check
        config = SimpleTestConfig(
            name="Test App",
            api_key="invalid-key",
            validation_level=ValidationLevel.BASIC,
        )
        assert config.api_key == "invalid-key"

        # No validation
        config = SimpleTestConfig(
            name=123,  # type: ignore - intentional for testing
            api_key="invalid-key",
            validation_level=ValidationLevel.NONE,
        )
        assert config.api_key == "invalid-key"
        assert config.name == "123"  # Pydantic still converts to string

    def test_required_in_environment(self) -> None:
        """Test validation for environment-specific required fields."""
        # Check required fields for development
        errors = SimpleTestConfig.validate_for_environment(Environment.DEVELOPMENT)
        assert len(errors) == 2  # missing name and api_key, which are required
        assert any("name" in e.context.get("config_key", "") for e in errors)
        assert any("api_key" in e.context.get("config_key", "") for e in errors)

        # Create a partially valid config
        config = SimpleTestConfig(name="Test App")
        errors = config.validate_for_environment(Environment.DEVELOPMENT)
        assert len(errors) == 1  # Only missing api_key now

        # Production doesn't require debug field
        config = SimpleTestConfig(
            name="Test App", api_key="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
        )
        errors = config.validate_for_environment(Environment.PRODUCTION)
        assert len(errors) == 0


class TestCrossFieldValidation:
    """Tests for cross-field validation."""

    def test_requires_decorator(self) -> None:
        """Test that the requires decorator enforces validation rules."""
        # Valid config: min_conn <= max_conn
        config = ValidatedConfig(min_conn=5, max_conn=10)
        assert config.min_conn == 5
        assert config.max_conn == 10

        # Invalid config: min_conn > max_conn
        with pytest.raises(ValidationError) as exc:
            ValidatedConfig(min_conn=15, max_conn=10)

        # Check error message
        assert "Minimum connections must be less than" in str(exc.value)

    def test_fields_dependency(self) -> None:
        """Test that fields_dependency enforces dependencies."""
        # Valid config: enable_retry=True with retry_interval
        config = ValidatedConfig(enable_retry=True, retry_interval=5)
        assert config.enable_retry is True
        assert config.retry_interval == 5

        # Invalid config: retry_interval without enable_retry
        with pytest.raises(ValidationError) as exc:
            ValidatedConfig(enable_retry=False, retry_interval=5)

        # Check error message
        assert "retry_interval requires enable_retry" in str(exc.value)

        # Valid config: both fields unset or enable_retry=True
        config = ValidatedConfig()  # Both have defaults, no retry_interval
        assert config.enable_retry is False
        assert config.retry_interval is None

    def test_format_pattern_validation(self) -> None:
        """Test format pattern validation for email."""
        # Valid email
        config = ValidatedConfig(email="test@example.com")
        assert config.email == "test@example.com"

        # Invalid email
        with pytest.raises(ValidationError):
            ValidatedConfig(email="not-an-email")

        # Basic validation level should skip format check
        config = ValidatedConfig(
            email="not-an-email", validation_level=ValidationLevel.BASIC
        )
        assert config.email == "not-an-email"


class TestSchemaGeneration:
    """Tests for schema information generation."""

    def test_discover_config_classes(self) -> None:
        """Test discovering config classes in a module."""
        # Discover configs in current module
        configs = discover_config_classes(__name__)

        # Should find our test configs
        config_names = [cls.__name__ for cls in configs]
        assert "SimpleTestConfig" in config_names
        assert "VersionedConfig" in config_names
        assert "ValidatedConfig" in config_names

    def test_export_schema_json(self) -> None:
        """Test exporting schema information as JSON."""
        # Export schema to JSON
        json_schema = export_schema_json(SimpleTestConfig)
        schema_data = json.loads(json_schema)

        # Verify schema contents
        assert schema_data["name"] == "SimpleTestConfig"
        assert schema_data["version"] == "1.0.0"
        assert "fields" in schema_data
        assert "name" in schema_data["fields"]
        assert "timeout" in schema_data["fields"]
        assert "api_key" in schema_data["fields"]

        # Check field details
        assert (
            schema_data["fields"]["name"]["description"]
            == "The name of the application"
        )
        assert schema_data["fields"]["name"]["example"] == "My App"
        assert (
            schema_data["fields"]["api_key"]["format_pattern"] == r"^[A-Za-z0-9]{32}$"
        )

    def test_export_schema_to_file(self) -> None:
        """Test exporting schema information to a file."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
            temp_path = Path(temp_file.name)

        try:
            # Export schema to file
            export_schema_json(SimpleTestConfig, output_path=temp_path)

            # Read the file and verify
            assert temp_path.exists()
            schema_data = json.loads(temp_path.read_text())

            # Verify schema contents
            assert schema_data["name"] == "SimpleTestConfig"
            assert "fields" in schema_data
            assert "name" in schema_data["fields"]
        finally:
            # Clean up
            if temp_path.exists():
                os.unlink(temp_path)

    def test_generate_markdown_docs(self) -> None:
        """Test generating markdown documentation."""
        # Generate docs for a single class
        markdown = generate_markdown_docs([SimpleTestConfig])

        # Verify markdown content
        assert "SimpleTestConfig" in markdown["SimpleTestConfig"]
        assert "# SimpleTestConfig Configuration" in markdown["SimpleTestConfig"]
        assert "**Version:** 1.0.0" in markdown["SimpleTestConfig"]

        # Check field documentation
        assert "### name" in markdown["SimpleTestConfig"]
        assert "The name of the application" in markdown["SimpleTestConfig"]
        assert "### timeout" in markdown["SimpleTestConfig"]
        assert "Timeout in seconds" in markdown["SimpleTestConfig"]

        # Check example
        assert "**Example:**" in markdown["SimpleTestConfig"]
        assert "My App" in markdown["SimpleTestConfig"]

    def test_generate_markdown_to_files(self) -> None:
        """Test generating markdown documentation to files."""
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Generate docs to directory
            generate_markdown_docs(
                [SimpleTestConfig, VersionedConfig], output_dir=temp_path
            )

            # Check files exist
            assert (temp_path / "SimpleTestConfig.md").exists()
            assert (temp_path / "VersionedConfig.md").exists()

            # Verify file contents
            simple_content = (temp_path / "SimpleTestConfig.md").read_text()
            versioned_content = (temp_path / "VersionedConfig.md").read_text()

            assert "# SimpleTestConfig Configuration" in simple_content
            assert "# VersionedConfig Configuration" in versioned_content


async def test_async_validation() -> None:
    """Test async validation scenario."""
    # This test ensures our validation works in async contexts
    config = await asyncio.gather(
        asyncio.create_task(
            asyncio.to_thread(lambda: ValidatedConfig(min_conn=5, max_conn=10))
        )
    )
    assert config[0].min_conn == 5
    assert config[0].max_conn == 10

    # Test schema_info works in async context
    schema_info = await asyncio.gather(
        asyncio.create_task(
            asyncio.to_thread(lambda: SimpleTestConfig.get_schema_info())
        )
    )
    assert schema_info[0]["name"] == "SimpleTestConfig"
