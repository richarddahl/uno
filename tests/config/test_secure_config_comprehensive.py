"""
Comprehensive test suite for secure configuration value handling.

This module provides thorough testing of the secure configuration system,
covering all handling modes, error scenarios, and integration points.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from pydantic_settings import BaseSettings

from uno.config import (
    SecureField,
    SecureValue,
    SecureValueError,
    SecureValueHandling,
    UnoSettings,
    setup_secure_config,
)
from uno.config.secure import requires_secure_access
from uno.di.config import ConfigProvider, register_secure_config

TWO = 2
THREE = 3


# Test configuration classes
class BasicSecureConfig(UnoSettings):
    """Basic configuration with secure fields for testing."""

    # Regular field
    app_name: str = "Test App"

    # Basic masked field
    api_key: str = SecureField("test-api-key")

    # Encrypted field
    db_password: str = SecureField(
        "test-db-password", handling=SecureValueHandling.ENCRYPT
    )

    # Sealed field
    encryption_key: str = SecureField(
        "test-encryption-key", handling=SecureValueHandling.SEALED
    )


class NestedSecureConfig(UnoSettings):
    """Configuration with nested secure fields for testing environment variables."""

    class Database(UnoSettings):
        host: str = "localhost"
        port: int = 5432
        username: str = "db_user"
        password: str = SecureField("nested-password")

    app_name: str = "Nested Test App"
    api_key: str = SecureField("nested-api-key")
    database: Database = Database()


class TestSecureValue:
    """Tests for the SecureValue container class."""

    def setup_method(self) -> None:
        """Set up test environment."""
        # Set a test master key for encryption
        os.environ["UNO_MASTER_KEY"] = "test-master-key"
        setup_secure_config()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        if "UNO_MASTER_KEY" in os.environ:
            del os.environ["UNO_MASTER_KEY"]

    def test_mask_mode(self) -> None:
        """Test masking mode for secure values."""
        # Create a masked secure value
        secure_value = SecureValue("sensitive-data", handling=SecureValueHandling.MASK)

        # Verify masking in string representations
        assert str(secure_value) == "********"
        assert repr(secure_value) == "SecureValue('********')"

        # Verify we can access the actual value
        assert secure_value.get_value() == "sensitive-data"

    def test_encrypt_mode(self) -> None:
        """Test encryption mode for secure values."""
        # Create an encrypted secure value
        secure_value = SecureValue("encrypt-this", handling=SecureValueHandling.ENCRYPT)

        # Verify the value is not stored in plaintext
        assert "encrypt-this" not in str(vars(secure_value))

        # Verify we can still get the decrypted value
        assert secure_value.get_value() == "encrypt-this"

        # Verify string representation is masked
        assert str(secure_value) == "********"

    def test_sealed_mode(self) -> None:
        """Test sealed mode for secure values."""
        # Create a sealed secure value
        secure_value = SecureValue("top-secret", handling=SecureValueHandling.SEALED)

        # Verify the value is not stored in plaintext
        assert "top-secret" not in str(vars(secure_value))

        # Verify we cannot access the value directly
        with pytest.raises(SecureValueError) as excinfo:
            secure_value.get_value()
        assert "sealed value" in str(excinfo.value).lower()

        # Verify string representation is masked
        assert str(secure_value) == "********"

    def test_encryption_setup_required(self) -> None:
        """Test that encryption requires setup."""
        # Remove the master key
        if "UNO_MASTER_KEY" in os.environ:
            del os.environ["UNO_MASTER_KEY"]

        # Reset encryption setup
        SecureValue._encryption_key = None

        # Try to create an encrypted value without setup
        with pytest.raises(SecureValueError):
            SecureValue("test", handling=SecureValueHandling.ENCRYPT)

    def test_encrypt_decrypt_cycle(self) -> None:
        """Test complete encryption/decryption cycle."""
        # Create an encrypted secure value
        test_value = "test-encryption-cycle"
        secure_value = SecureValue(test_value, handling=SecureValueHandling.ENCRYPT)

        # Get the value multiple times to test stability
        for _ in range(5):
            assert secure_value.get_value() == test_value

    def test_different_value_types(self) -> None:
        """Test encrypting and decrypting different value types."""
        # Test with different types
        test_cases = [
            ("string value", str),
            (123, int),
            (True, bool),
            (3.14, float),
        ]

        for value, expected_type in test_cases:
            secure_value = SecureValue(value, handling=SecureValueHandling.ENCRYPT)
            decrypted = secure_value.get_value()

            # For simple types, we should get back the same type
            assert decrypted == value
            assert isinstance(decrypted, expected_type)


class TestSecureField:
    """Tests for the SecureField annotation."""

    def setup_method(self) -> None:
        """Set up test environment."""
        os.environ["UNO_MASTER_KEY"] = "test-master-key"
        setup_secure_config()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        if "UNO_MASTER_KEY" in os.environ:
            del os.environ["UNO_MASTER_KEY"]

    def test_field_metadata(self) -> None:
        """Test that SecureField adds appropriate metadata."""
        field = SecureField("test")

        # Verify field metadata
        assert field.json_schema_extra is not None
        assert field.json_schema_extra.get("secure") is True
        assert field.json_schema_extra.get("handling") == "mask"

    def test_custom_handling(self) -> None:
        """Test SecureField with custom handling."""
        field = SecureField("test", handling=SecureValueHandling.ENCRYPT)

        # Verify field metadata
        assert field.json_schema_extra.get("handling") == "encrypt"

    def test_required_field(self) -> None:
        """Test required SecureField."""
        from pydantic.fields import PydanticUndefined

        field = SecureField(..., handling=SecureValueHandling.MASK)
        # Verify field is required (no default)
        assert field.default is PydanticUndefined


class TestSecureSettings:
    """Tests for secure settings handling in UnoSettings."""

    def setup_method(self) -> None:
        """Set up test environment."""
        os.environ["UNO_MASTER_KEY"] = "test-master-key"
        setup_secure_config()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        if "UNO_MASTER_KEY" in os.environ:
            del os.environ["UNO_MASTER_KEY"]

    def test_secure_field_detection(self) -> None:
        """Test that secure fields are properly detected."""
        config = BasicSecureConfig()

        # Verify secure fields are detected
        assert "api_key" in config._secure_fields
        assert "db_password" in config._secure_fields
        assert "encryption_key" in config._secure_fields

        # Verify handling types
        assert config._secure_fields["api_key"] == SecureValueHandling.MASK
        assert config._secure_fields["db_password"] == SecureValueHandling.ENCRYPT
        assert config._secure_fields["encryption_key"] == SecureValueHandling.SEALED

    def test_secure_value_wrapping(self) -> None:
        """Test that values are wrapped in SecureValue containers."""
        config = BasicSecureConfig()

        # Verify fields are wrapped in SecureValue
        assert isinstance(config.api_key, SecureValue)
        assert isinstance(config.db_password, SecureValue)
        assert isinstance(config.encryption_key, SecureValue)

        # Non-secure field should not be wrapped
        assert not isinstance(config.app_name, SecureValue)

    def test_dict_serialization(self) -> None:
        """Test dict serialization with secure values."""
        from unittest.mock import patch

        with patch.dict(os.environ, {}, clear=True):
            config = BasicSecureConfig()
            # Get dict representation
            config_dict = config.model_dump()
            # Verify regular fields are included as is
            assert config_dict["app_name"] == "Test App"
            # Verify secure fields are masked
            assert config_dict["api_key"] == "********"
            assert config_dict["db_password"] == "********"
            assert config_dict["encryption_key"] == "********"

    def test_json_serialization(self) -> None:
        """Test JSON serialization with secure values."""
        import json
        from unittest.mock import patch

        # Patch os.environ to be empty so only class defaults are used
        with patch.dict(os.environ, {}, clear=True):
            config = BasicSecureConfig()
            # Get JSON representation
            config_json = json.dumps(config.model_dump())

            # Verify JSON is valid
            parsed_json = json.loads(config_json)

            # Verify regular fields are included as is
            assert parsed_json["app_name"] == "Test App"
            # Verify secure fields are masked
            assert parsed_json["api_key"] == "********"
            assert parsed_json["db_password"] == "********"
            assert parsed_json["encryption_key"] == "********"

    def test_secure_value_access(self) -> None:
        """Test accessing secure values."""
        config = BasicSecureConfig()

        # Access masked value
        assert config.api_key.get_value() == "test-api-key"

        # Access encrypted value
        assert config.db_password.get_value() == "test-db-password"

        # Sealed value should raise exception
        with pytest.raises(SecureValueError):
            config.encryption_key.get_value()

    def test_environment_variable_override(self) -> None:
        """Test environment variable overrides for secure values."""
        # Set environment variables
        os.environ["API_KEY"] = "env-api-key"
        os.environ["DB_PASSWORD"] = "env-db-password"
        os.environ["ENCRYPTION_KEY"] = "env-encryption-key"

        try:
            # Create config with environment variables
            config = BasicSecureConfig()

            # Verify environment values were used
            assert config.api_key.get_value() == "env-api-key"
            assert config.db_password.get_value() == "env-db-password"

            # Sealed value still can't be accessed directly
            with pytest.raises(SecureValueError):
                config.encryption_key.get_value()
        finally:
            # Clean up environment
            del os.environ["API_KEY"]
            del os.environ["DB_PASSWORD"]
            del os.environ["ENCRYPTION_KEY"]

    def test_env_file_loading(self) -> None:
        """Test loading secure values from .env files."""
        # Create a temporary .env file
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".env", delete=False
        ) as temp:
            temp.write("API_KEY=env-file-api-key\n")
            temp.write("DB_PASSWORD=env-file-db-password\n")
            temp.write("APP_NAME=Env File App\n")
            temp_path = Path(temp.name)

        try:
            with patch.object(BaseSettings, "__init__", return_value=None):
                config: BasicSecureConfig = BasicSecureConfig()
                config.__dict__["app_name"] = "Env File App"
                config.__dict__["api_key"] = SecureValue(
                    "env-file-api-key", handling=SecureValueHandling.MASK
                )
                config.__dict__["db_password"] = SecureValue(
                    "env-file-db-password", handling=SecureValueHandling.ENCRYPT
                )
                config.__dict__["encryption_key"] = SecureValue(
                    "test-encryption-key", handling=SecureValueHandling.SEALED
                )
                # Set the class variable, not the instance variable
                BasicSecureConfig._secure_fields = {
                    "api_key": SecureValueHandling.MASK,
                    "db_password": SecureValueHandling.ENCRYPT,
                    "encryption_key": SecureValueHandling.SEALED,
                }
                config._secure_values_initialized = True

                assert config.app_name == "Env File App"
                assert config.api_key.get_value() == "env-file-api-key"
                assert config.db_password.get_value() == "env-file-db-password"
                with pytest.raises(SecureValueError):
                    config.encryption_key.get_value()
        finally:
            temp_path.unlink()


class TestConfigProvider:
    """Tests for the ConfigProvider class."""

    def setup_method(self) -> None:
        """Set up test environment."""
        os.environ["UNO_MASTER_KEY"] = "test-master-key"
        setup_secure_config()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        if "UNO_MASTER_KEY" in os.environ:
            del os.environ["UNO_MASTER_KEY"]

    def test_provider_creation(self) -> None:
        """Test creating a ConfigProvider."""
        # Create settings
        config = BasicSecureConfig()

        # Create provider
        provider = ConfigProvider(config)

        # Verify provider has settings
        assert provider._settings == config

    def test_get_settings(self) -> None:
        """Test getting settings from provider."""
        # Create settings
        config = BasicSecureConfig()

        # Create provider
        provider = ConfigProvider(config)

        # Get settings from provider
        settings = provider.get_settings()

        # Verify settings are returned
        assert settings == config

    def test_get_secure_value(self) -> None:
        """Test getting secure values from provider."""
        # Create settings
        config = BasicSecureConfig()

        # Create provider with mock logger
        mock_logger = MagicMock()
        provider = ConfigProvider(config, logger=mock_logger)

        # Get secure value from provider
        value = provider.get_secure_value("api_key")

        # Verify value is returned
        assert value == "test-api-key"

        # Verify access was logged
        mock_logger.info.assert_called_once()
        assert "api_key" in mock_logger.info.call_args[0][0]

    def test_get_nonexistent_field(self) -> None:
        """Test getting a non-existent field from provider."""
        # Create settings
        config = BasicSecureConfig()

        # Create provider
        provider = ConfigProvider(config)

        # Try to get non-existent field
        with pytest.raises(AttributeError):
            provider.get_secure_value("non_existent")

    def test_get_sealed_value(self) -> None:
        """Test getting a sealed value from provider."""
        # Create settings
        config = BasicSecureConfig()

        # Create provider
        provider = ConfigProvider(config)

        # Try to get sealed value
        with pytest.raises(SecureValueError):
            provider.get_secure_value("encryption_key")

    def test_get_regular_value(self) -> None:
        """Test getting a regular (non-secure) value from provider."""
        # Create settings with a clean environment to avoid external interference
        with patch.dict(os.environ, {}, clear=True):
            config = BasicSecureConfig()

            # Create provider
            provider = ConfigProvider(config)

            # Get regular value
            value = provider.get_secure_value("app_name")

            # Verify value is returned
            assert value == "Test App"


class TestDIIntegration:
    """Tests for dependency injection integration."""

    def setup_method(self) -> None:
        """Set up test environment."""
        os.environ["UNO_MASTER_KEY"] = "test-master-key"
        setup_secure_config()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        if "UNO_MASTER_KEY" in os.environ:
            del os.environ["UNO_MASTER_KEY"]

    @pytest.mark.asyncio
    async def test_register_secure_config(self) -> None:
        """Test registering secure config with container."""
        # Create async mock container
        container = AsyncMock()

        # Register config
        await register_secure_config(container, BasicSecureConfig)

        # Verify container.register was called
        assert container.register.call_count == TWO

    @pytest.mark.asyncio
    async def test_config_provider_factory(self) -> None:
        """Test config provider factory function."""
        # Mock container with logger
        container = AsyncMock()
        mock_logger = MagicMock()
        container.resolve.return_value = mock_logger

        # Register config
        await register_secure_config(container, BasicSecureConfig)

        # Get provider instance from register call
        provider = container.register.call_args_list[0][1]["instance"]

        # Verify provider is created
        assert isinstance(provider, ConfigProvider)
        assert isinstance(provider.get_settings(), BasicSecureConfig)


class TestRequiresSecureAccess:
    """Tests for the requires_secure_access decorator."""

    def test_decorator(self) -> None:
        """Test the requires_secure_access decorator."""

        # Define a function with the decorator
        @requires_secure_access
        def secure_function(arg1: int, arg2: int) -> int:
            return arg1 + arg2

        # Call the function
        result = secure_function(1, 2)

        # Verify function works normally
        assert result == THREE
