"""Tests for configuration error classes."""

from __future__ import annotations

import pytest

from uno.config.errors import (
    ConfigError,
    ConfigEnvironmentError,
    ConfigFileNotFoundError,
    ConfigMissingKeyError,
    ConfigParseError,
    ConfigValidationError,
    SecureConfigError,
    SecureValueError,
)
from uno.errors.base import ErrorCode, ErrorCategory, ErrorSeverity, UnoError


class TestConfigErrors:
    """Test configuration error hierarchy."""

    def test_base_config_error(self) -> None:
        """Test the base ConfigError class."""
        # Create with default code
        error = ConfigError("Test error message")
        assert error.message == "Test error message"
        assert error.code.code == "CONFIG_ERROR"
        assert isinstance(error, UnoError)

        # Create with custom code and context
        custom_code = ErrorCode.get_or_create(
            "CUSTOM_CONFIG_ERROR", ErrorCategory.get_or_create("CONFIG")
        )
        context = {"key": "value"}

        error = ConfigError(
            message="Custom error",
            code=custom_code,
            severity=ErrorSeverity.WARNING,
            context=context,
        )

        assert error.message == "Custom error"
        assert error.code.code == "CUSTOM_CONFIG_ERROR"
        assert error.severity == ErrorSeverity.WARNING
        assert error.context["key"] == "value"

    def test_config_validation_error(self) -> None:
        """Test ConfigValidationError."""
        error = ConfigValidationError(
            message="Invalid configuration value",
            config_key="port",
            config_value="invalid",
        )

        assert "Invalid configuration value" in error.message
        assert error.code.code == "CONFIG_VALIDATION_ERROR"
        assert error.context["config_key"] == "port"
        assert error.context["config_value"] == "invalid"

    def test_config_file_errors(self) -> None:
        """Test file-related configuration errors."""
        # Test file not found
        not_found = ConfigFileNotFoundError("/path/to/config.json")
        assert "not found" in not_found.message
        assert not_found.context["file_path"] == "/path/to/config.json"

        # Test parse error
        parse_error = ConfigParseError(
            file_path="/path/to/config.json", reason="Invalid JSON", line_number=42
        )

        assert "Failed to parse" in parse_error.message
        assert "line 42" in parse_error.message
        assert parse_error.context["file_path"] == "/path/to/config.json"
        assert parse_error.context["reason"] == "Invalid JSON"
        assert parse_error.context["line_number"] == 42

    def test_secure_value_errors(self) -> None:
        """Test secure value errors."""
        # Test basic secure value error
        error = SecureValueError("Failed to decrypt value")
        assert "Failed to decrypt value" in error.message
        assert error.code.code == "CONFIG_SECURE_VALUE_ERROR"

        # Test with custom code
        custom_code = ErrorCode.get_or_create(
            "CONFIG_SECURE_KEY_ERROR", ErrorCategory.get_or_create("CONFIG")
        )
        error = SecureValueError(message="Key rotation failed", code=custom_code)

        assert "Key rotation failed" in error.message
        assert error.code.code == "CONFIG_SECURE_KEY_ERROR"

        # Verify inheritance
        assert isinstance(error, ConfigError)
        assert isinstance(error, SecureConfigError)
