"""Tests for configuration error hierarchy."""

from __future__ import annotations

import pytest

from uno.config.errors import (
    ConfigError,
    ConfigEnvironmentError,
    ConfigFileNotFoundError,
    ConfigMissingKeyError,
    ConfigParseError,
    ConfigValidationError,
    SecureValueError,
)
from uno.errors.base import ErrorCategory, ErrorSeverity, UnoError


class TestErrorHierarchy:
    """Test the configuration error hierarchy."""

    def test_config_error_base(self) -> None:
        """Test the base ConfigError class."""
        error = ConfigError("Test error")
        assert error.message == "Test error"
        assert error.code == "CONFIG_ERROR"
        assert error.category == ErrorCategory.CONFIG
        assert error.severity == ErrorSeverity.ERROR

        # Test with custom code
        error = ConfigError("Test error", code="CUSTOM")
        assert error.code == "CONFIG_CUSTOM"

    def test_config_validation_error(self) -> None:
        """Test ConfigValidationError."""
        error = ConfigValidationError(
            "Invalid config", config_key="test_key", config_value="test_value"
        )
        assert error.message == "Invalid config"
        assert error.code == "CONFIG_VALIDATION_ERROR"
        assert error.context["config_key"] == "test_key"
        assert error.context["config_value"] == "test_value"

    def test_config_file_not_found_error(self) -> None:
        """Test ConfigFileNotFoundError."""
        error = ConfigFileNotFoundError("/path/to/config.yaml")
        assert "Configuration file not found" in error.message
        assert error.code == "CONFIG_FILE_NOT_FOUND"
        assert error.context["file_path"] == "/path/to/config.yaml"

    def test_config_parse_error(self) -> None:
        """Test ConfigParseError."""
        error = ConfigParseError("/path/to/config.yaml", "Syntax error", line_number=42)
        assert "Failed to parse configuration file" in error.message
        assert "line 42" in error.message
        assert error.code == "CONFIG_PARSE_ERROR"
        assert error.context["file_path"] == "/path/to/config.yaml"
        assert error.context["reason"] == "Syntax error"
        assert error.context["line_number"] == 42

    def test_config_missing_key_error(self) -> None:
        """Test ConfigMissingKeyError."""
        error = ConfigMissingKeyError("database_url")
        assert "Required configuration key missing" in error.message
        assert error.code == "CONFIG_MISSING_KEY"
        assert error.context["key"] == "database_url"

    def test_config_environment_error(self) -> None:
        """Test ConfigEnvironmentError."""
        error = ConfigEnvironmentError(
            "Environment not supported", environment="staging"
        )
        assert error.message == "Environment not supported"
        assert error.code == "CONFIG_ENVIRONMENT_ERROR"
        assert error.context["environment"] == "staging"

    def test_secure_value_error(self) -> None:
        """Test SecureValueError inherits from ConfigError.

        Note: This test will fail with the current implementation and should pass
        after fixing the inheritance hierarchy.
        """
        error = SecureValueError("Encryption failed", code="KEY_ERROR")

        # Should inherit from ConfigError
        assert isinstance(error, ConfigError)
        assert error.message == "Encryption failed"
        assert error.code == "CONFIG_SECURE_KEY_ERROR"
        assert error.category == ErrorCategory.CONFIG

        # Check the whole inheritance chain
        assert isinstance(error, UnoError)
        assert isinstance(error, ConfigError)
        assert isinstance(error, SecureValueError)
