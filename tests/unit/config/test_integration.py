"""Integration tests for the configuration system."""

from __future__ import annotations

import os
import tempfile  # Add missing tempfile import
from pathlib import Path
from typing import Any

import pytest
from pydantic import Field, ValidationError
from cryptography.fernet import Fernet

from uno.config import (
    Environment,
    SecureField,
    SecureValue,
    SecureValueHandling,
    Config,
    get_config,
    load_settings,
)
from uno.config.errors import ConfigError, SecureValueError
from uno.config.key_rotation import rotate_secure_values, setup_key_rotation
from uno.config.injection import ConfigRegistrationExtensions
from uno.config.env_loader import load_env_files  # Import for env_loader functions


class TestConfigIntegration:
    """Test end-to-end configuration scenarios."""

    @pytest.mark.asyncio
    async def test_layered_configuration(
        self,
        setup_secure_config: None,
        env_dir: Path,
        save_env_vars,
    ) -> None:
        """Test layered configuration with multiple sources."""

        # Create env files with proper formatting and make sure paths are correct
        (env_dir / ".env").write_text(
            "DATABASE__HOST=base.example.com\n" "APPLICATION__NAME=Base App\n"
        )

        (env_dir / ".env.development").write_text(
            "DATABASE__HOST=dev.example.com\n"
            "DATABASE__PORT=5433\n"
            "APPLICATION__DEBUG=true\n"
        )

        # Set environment variables (highest priority)
        os.environ["DATABASE__USERNAME"] = "dev_user"
        os.environ["APPLICATION__PORT"] = "9000"

        # Make sure we're in the right directory when loading settings
        original_dir = os.getcwd()
        os.chdir(env_dir)

        try:
            # Explicitly load env files before loading settings - make sure they're loaded with override=True
            env_vars = load_env_files(
                env=Environment.DEVELOPMENT, base_dir=env_dir, override=True
            )

            # Verify env vars were actually loaded into environment
            assert "DATABASE__HOST" in os.environ
            assert os.environ["DATABASE__HOST"] == "dev.example.com"

            # Define settings classes *after* env vars are loaded
            class DatabaseSettings(Config):
                model_config = {
                    "env_nested_delimiter": "__",
                    "extra": "ignore",
                    "env_prefix": "DATABASE__",  # Explicitly set the prefix
                }

                host: str = Field("localhost", env="HOST")  # Explicit env var mapping
                port: int = Field(5432, env="PORT")
                username: str = Field("postgres", env="USERNAME")
                password: str = SecureField("", handling=SecureValueHandling.ENCRYPT)
                database: str = "app_db"

            class ApplicationSettings(Config):
                model_config = {
                    "env_nested_delimiter": "__",
                    "extra": "ignore",
                    "env_prefix": "APPLICATION__",  # Explicitly set the prefix
                }

                name: str = Field("Uno Application", env="NAME")
                version: str = "1.0.0"
                debug: bool = Field(False, env="DEBUG")
                port: int = Field(8000, env="PORT")

            # Load database settings - force direct update from env
            db_settings = await load_settings(
                DatabaseSettings,
                env=Environment.DEVELOPMENT,
                config_path=str(env_dir),
            )

            # Debug: print actual loaded values to help diagnose issues
            print(f"Loaded host: {db_settings.host}")
            print(f"Env var: {os.environ.get('DATABASE__HOST')}")

            # Verify layered configuration with correct precedence
            assert db_settings.host == "dev.example.com"  # From .env.development
            assert db_settings.port == 5433  # From .env.development
            assert db_settings.username == "dev_user"  # From environment
            assert db_settings.database == "app_db"  # Default value

            # Load application settings
            app_settings = await load_settings(
                ApplicationSettings,
                env=Environment.DEVELOPMENT,
                config_path=str(env_dir),
            )

            # Verify layered configuration with correct precedence
            assert app_settings.name == "Base App"  # From .env
            assert app_settings.debug is True  # From .env.development
            assert app_settings.port == 9000  # From environment
            assert app_settings.version == "1.0.0"  # Default value
        finally:
            # Restore original directory
            os.chdir(original_dir)

    @pytest.mark.asyncio
    async def test_config_dependency_injection(
        self,
        setup_secure_config: None,
        mock_container: Any,
        clear_config_cache: None,
    ) -> None:
        """Test integrating configuration with dependency injection."""

        # Create settings class with secure fields for a more thorough test
        class AppSettings(Config):
            name: str = "test_app"
            port: int = 8000
            api_key: Any = SecureField("test_key", handling=SecureValueHandling.ENCRYPT)

        # The setup_secure_config fixture has already initialized secure config
        # so we don't need to call setup_secure_config() again

        # Register with container
        app_settings = await load_settings(AppSettings)

        # Debug to see what type the api_key actually is
        assert isinstance(
            app_settings.api_key, SecureValue
        ), f"api_key is of type {type(app_settings.api_key)}, expected SecureValue"

        # Verify secure field is properly wrapped as SecureValue
        assert hasattr(app_settings.api_key, "get_value")
        assert await app_settings.api_key.get_value() == "test_key"

        ConfigRegistrationExtensions.register_configuration(
            mock_container, app_settings
        )

        # Should be resolvable by concrete type
        resolved_concrete = mock_container.resolve(AppSettings)
        assert resolved_concrete is app_settings
        assert resolved_concrete.name == "test_app"

        # Should be resolvable by interface
        from uno.config.protocols import ConfigProtocol

        resolved_interface = mock_container.resolve(ConfigProtocol)
        assert resolved_interface is app_settings

    @pytest.mark.asyncio
    async def test_key_rotation_integration(self, test_encryption_key: bytes) -> None:
        """Test key rotation with multiple secure values."""
        # Set up with initial key
        await setup_key_rotation(
            old_key=test_encryption_key,
            new_key=Fernet.generate_key(),
            old_version="old_key",
            new_version="new_key",
        )

        # Create multiple secure values
        values = [
            SecureValue("value1", handling=SecureValueHandling.ENCRYPT),
            SecureValue("value2", handling=SecureValueHandling.ENCRYPT),
            SecureValue("value3", handling=SecureValueHandling.ENCRYPT),
        ]

        # Rotate all values to new key
        await rotate_secure_values(values, "new_key")

        # All values should be accessible and rotated
        assert await values[0].get_value() == "value1"
        assert await values[1].get_value() == "value2"
        assert await values[2].get_value() == "value3"
        assert all(v._key_version == "new_key" for v in values)

    @pytest.mark.asyncio
    async def test_edge_cases(
        self,
        setup_secure_config: None,
        save_env_vars,
        clear_config_cache: None,  # Clear cache to ensure fresh test
    ) -> None:
        """Test various edge cases in configuration system."""
        try:
            # Test with invalid environment variable types - set directly in os.environ
            os.environ["INT_VALUE"] = "not_an_int"

            # Define class that directly references the environment variable
            class EdgeSettings(Config):
                model_config = {
                    "env_nested_delimiter": "__",
                    "extra": "ignore",
                    "validate_assignment": True,
                    # Add explicit env vars mapping to ensure it's picked up
                    "env_prefix": "",  # No prefix
                }

                int_value: int

            # Should raise validation error - this should happen during initialization
            with pytest.raises(ValidationError):
                # The error happens during class instantiation due to Pydantic validation
                _ = EdgeSettings()

        finally:
            # Clean up environment variables before next test
            os.environ.pop("INT_VALUE", None)

        # Test with empty environment files
        with tempfile.TemporaryDirectory() as tmp_dir:
            empty_dir = Path(tmp_dir)
            (empty_dir / ".env").touch()  # Create empty file

            # Define a new settings class to avoid validation issues from previous test
            class EmptyFileSettings(Config):
                int_value: int = 42

            # Should not raise errors with empty file
            settings = await load_settings(
                EmptyFileSettings, config_path=str(empty_dir)
            )
            assert settings.int_value == 42  # Should use default
