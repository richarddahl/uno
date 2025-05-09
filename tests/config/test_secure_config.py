"""
Test file for secure configuration handling.

This module contains tests for the secure configuration value handling
capabilities in the Uno configuration system.
"""

import os

import pytest

from uno.config import (
    SecureField,
    SecureValue,
    SecureValueHandling,
    UnoSettings,
    setup_secure_config,
)
from uno.config.secure import SecureValueError


class SecurityConfig(UnoSettings):
    """Test configuration class with secure fields."""

    # Regular field (not secure)
    app_name: str = "Test App"

    # Field with simple masking (plaintext in memory, masked in logs)
    api_key: str = SecureField("default-key")

    # Field with encryption (encrypted in storage, decrypted when accessed)
    db_password: str = SecureField(
        "secret-db-password", handling=SecureValueHandling.ENCRYPT
    )

    # Field that's always encrypted (even in memory)
    jwt_secret: str = SecureField(
        "super-secret-jwt-token", handling=SecureValueHandling.SEALED
    )


class TestSecureSettings:
    """Tests for secure configuration values."""

    def setup_method(self) -> None:
        """Set up test environment."""
        # Set a test master key for encryption
        os.environ["UNO_MASTER_KEY"] = "test-master-key"
        setup_secure_config()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        if "UNO_MASTER_KEY" in os.environ:
            del os.environ["UNO_MASTER_KEY"]

    def test_masking_in_representation(self) -> None:
        """Test that secure values are masked in string representations."""
        import json
        from unittest.mock import patch

        with patch.dict(os.environ, {}, clear=True):
            config = SecurityConfig()
            # Dict serialization should mask secure values
            config_dict = config.model_dump()
            assert config_dict["app_name"] == "Test App"
            assert config_dict["api_key"] == "********"
            assert config_dict["db_password"] == "********"
            assert config_dict["jwt_secret"] == "********"
            # JSON serialization should also mask secure values
            config_json = json.dumps(config_dict)
            assert "Test App" in config_json
            assert "default-key" not in config_json
            assert "secret-db-password" not in config_json
            assert "super-secret-jwt-token" not in config_json
            assert "********" in config_json

    def test_masked_value_access(self) -> None:
        """Test access to values with MASK handling."""
        config = SecurityConfig()

        # Masked values should be accessible directly
        api_key_field = config.api_key
        assert isinstance(api_key_field, SecureValue)
        assert str(api_key_field) == "********"
        assert api_key_field.get_value() == "default-key"

    def test_encrypted_value_access(self) -> None:
        """Test access to values with ENCRYPT handling."""
        config = SecurityConfig()

        # Encrypted values should be accessible via get_value()
        db_password_field = config.db_password
        assert isinstance(db_password_field, SecureValue)
        assert str(db_password_field) == "********"
        assert db_password_field.get_value() == "secret-db-password"

    def test_sealed_value_access(self) -> None:
        """Test access to values with SEALED handling."""
        config = SecurityConfig()

        # Sealed values should not be accessible directly
        jwt_secret_field = config.jwt_secret
        assert isinstance(jwt_secret_field, SecureValue)
        assert str(jwt_secret_field) == "********"

        # Accessing sealed values should raise an exception
        with pytest.raises(SecureValueError) as excinfo:
            jwt_secret_field.get_value()
        assert "sealed value" in str(excinfo.value).lower()

    def test_environment_variables(self) -> None:
        """Test loading secure values from environment variables."""
        # Set environment variables for secure fields
        os.environ["API_KEY"] = "env-api-key"
        os.environ["DB_PASSWORD"] = "env-db-password"
        os.environ["JWT_SECRET"] = "env-jwt-secret"

        try:
            # Create config with environment variables
            config = SecurityConfig()

            # Verify values are loaded from environment
            assert config.api_key.get_value() == "env-api-key"
            assert config.db_password.get_value() == "env-db-password"

            # Sealed value still can't be accessed
            with pytest.raises(SecureValueError):
                config.jwt_secret.get_value()
        finally:
            # Clean up environment
            del os.environ["API_KEY"]
            del os.environ["DB_PASSWORD"]
            del os.environ["JWT_SECRET"]
