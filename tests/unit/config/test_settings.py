"""Tests for Config base class and settings loading."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from pydantic import Field, ValidationError

from uno.config import (
    Environment,
    SecureField,
    SecureValueHandling,
    Config,
    get_config,
    load_settings,
)
from uno.config.protocols import SecureAccessibleProtocol
from uno.config.settings import clear_config_cache


class TestEnvironment:
    """Test Environment enum functionality."""

    def test_environment_enum(self) -> None:
        """Test Environment enum string conversion."""
        # Test string conversion
        assert Environment.from_string("dev") == Environment.DEVELOPMENT
        assert Environment.from_string("development") == Environment.DEVELOPMENT
        assert Environment.from_string("test") == Environment.TESTING
        assert Environment.from_string("testing") == Environment.TESTING
        assert Environment.from_string("prod") == Environment.PRODUCTION
        assert Environment.from_string("production") == Environment.PRODUCTION

        # Test default for None
        assert Environment.from_string(None) == Environment.DEVELOPMENT

        # Test invalid environment
        with pytest.raises(Exception) as exc_info:
            Environment.from_string("invalid")
        assert "Invalid environment" in str(exc_info.value)

    def test_get_current(self, save_env_vars) -> None:
        """Test getting current environment from env vars."""
        # Test UNO_ENV takes precedence
        os.environ["UNO_ENV"] = "production"
        os.environ["ENVIRONMENT"] = "development"
        os.environ["ENV"] = "testing"
        assert Environment.get_current() == Environment.PRODUCTION

        # Test fallback to ENVIRONMENT
        os.environ.pop("UNO_ENV")
        assert Environment.get_current() == Environment.DEVELOPMENT

        # Test fallback to ENV
        os.environ.pop("ENVIRONMENT")
        assert Environment.get_current() == Environment.TESTING

        # Test default when no env vars are set
        os.environ.pop("ENV")
        assert Environment.get_current() == Environment.DEVELOPMENT


class TestConfig:
    """Test Config base class functionality."""

    @pytest.mark.asyncio
    async def test_basic_settings_loading(
        self, clear_config_cache, save_env_vars
    ) -> None:
        """Test basic settings loading."""
        # Set test environment variables
        os.environ["APP_NAME"] = "env_app"
        os.environ["PORT"] = "9000"

        # Create settings class
        class TestSettings(Config):
            app_name: str = "default_app"
            port: int = 8000

        # Load settings
        settings = await load_settings(TestSettings)

        # Check values loaded from environment
        assert settings.app_name == "env_app"
        assert settings.port == 9000

    @pytest.mark.asyncio
    async def test_from_env_loading(
        self, temp_env_files: tuple[Path, Path, Path]
    ) -> None:
        """Test loading settings from environment-specific files."""

        # Define test settings class
        class TestEnvSettings(Config):
            base_setting: str = ""
            dev_setting: str = ""
            local_setting: str = ""
            override_setting: str = ""

        # Load settings from development environment
        settings = await load_settings(TestEnvSettings, env=Environment.DEVELOPMENT)

        # Should have loaded values from all env files with correct priority
        assert settings.base_setting == "base_value"
        assert settings.dev_setting == "dev_value"
        assert settings.local_setting == "local_value"
        assert settings.override_setting == "local_override"  # Highest priority

    @pytest.mark.asyncio
    async def test_override_values(self, save_env_vars) -> None:
        """Test explicit override values take precedence."""
        # Set environment variables
        os.environ["APP_NAME"] = "env_app"
        os.environ["PORT"] = "9000"

        # Create settings class
        class TestSettings(Config):
            app_name: str = "default_app"
            port: int = 8000

        # Load settings with overrides
        overrides = {"app_name": "override_app", "port": 1234}
        settings = await load_settings(TestSettings, override_values=overrides)

        # Check overrides take precedence
        assert settings.app_name == "override_app"
        assert settings.port == 1234

    @pytest.mark.asyncio
    async def test_config_cache(self, clear_config_cache) -> None:
        """Test config caching."""
        # The fixture returns None but clears the cache as a side effect

        # Define simple settings class
        class CacheTestSettings(Config):
            value: str = "original"

        # First call should load settings
        settings1 = await get_config(CacheTestSettings)

        # Modify the value to test caching
        settings1.value = "modified"

        # Second call should return cached instance
        settings2 = await get_config(CacheTestSettings)

        # Should be the same modified instance
        assert settings2 is settings1
        assert settings2.value == "modified"

        # Clear cache using imported function, not the fixture
        from uno.config.settings import clear_config_cache

        clear_config_cache()

        # Should load fresh instance
        settings3 = await get_config(CacheTestSettings)
        assert settings3 is not settings1
        assert settings3.value == "original"


class TestSecureFields:
    """Test secure field handling in settings."""

    def test_secure_fields_isolation(self, setup_secure_config: None) -> None:
        """Test that secure fields are isolated between different settings classes."""

        # Define first settings class with secure fields
        class FirstSecureSettings(Config):
            password: Any = SecureField("password1", handling=SecureValueHandling.MASK)
            api_key: Any = SecureField("api1", handling=SecureValueHandling.ENCRYPT)

        # Define second settings class with different secure fields
        class SecondSecureSettings(Config):
            token: Any = SecureField("token2", handling=SecureValueHandling.MASK)
            secret: Any = SecureField("secret2", handling=SecureValueHandling.ENCRYPT)

        # Create instances
        first = FirstSecureSettings()
        second = SecondSecureSettings()

        # Check that secure fields are correctly tracked for each class
        assert "password" in first._secure_fields
        assert "api_key" in first._secure_fields
        assert "token" not in first._secure_fields
        assert "secret" not in first._secure_fields

        assert "token" in second._secure_fields
        assert "secret" in second._secure_fields
        assert "password" not in second._secure_fields
        assert "api_key" not in second._secure_fields

    @pytest.mark.asyncio
    async def test_model_serialization(self, setup_secure_config: None) -> None:
        """Test model serialization with secure fields."""

        class SerializeSettings(Config):
            normal: str = "normal_value"
            password: Any = SecureField(
                "secret_value", handling=SecureValueHandling.MASK
            )
            api_key: Any = SecureField("api_key", handling=SecureValueHandling.ENCRYPT)

        settings = SerializeSettings()

        # Verify we can access secure values
        assert await settings.password.get_value() == "secret_value"
        assert await settings.api_key.get_value() == "api_key"

        # Test dict serialization
        settings_dict = settings.model_dump()
        assert settings_dict["normal"] == "normal_value"
        assert settings_dict["password"] == "******"  # Masked
        assert settings_dict["api_key"] == "******"  # Masked

        # Test json serialization
        settings_json = settings.model_dump_json()
        assert "normal_value" in settings_json
        assert "secret_value" not in settings_json
        assert "password" in settings_json
        assert "api_key" in settings_json
        assert "******" in settings_json  # Masked values
