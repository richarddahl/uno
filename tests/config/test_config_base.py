"""Tests for the Uno configuration system.

This module contains tests for the configuration foundation components,
including environment management, settings classes, and file loading.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

from uno.config import (
    ConfigError,
    Environment,
    UnoSettings,
    get_config,
    get_env_value,
    load_env_files,
    load_settings,
)

if TYPE_CHECKING:
    from pathlib import Path


PORT_8000 = 8000
PORT_5000 = 5000
PORT_4000 = 4000
PORT_5433 = 5433


class TestEnvironment:
    """Tests for the Environment enum and related functionality."""

    def test_environment_values(self) -> None:
        """Test that the Environment enum has the expected values."""
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.TESTING.value == "testing"
        assert Environment.PRODUCTION.value == "production"

    def test_from_string_valid_values(self) -> None:
        """Test converting valid string values to Environment enum."""
        # Test development variants
        assert Environment.from_string("development") == Environment.DEVELOPMENT
        assert Environment.from_string("dev") == Environment.DEVELOPMENT
        assert Environment.from_string("DEV") == Environment.DEVELOPMENT

        # Test testing variants
        assert Environment.from_string("testing") == Environment.TESTING
        assert Environment.from_string("test") == Environment.TESTING
        assert Environment.from_string("TEST") == Environment.TESTING

        # Test production variants
        assert Environment.from_string("production") == Environment.PRODUCTION
        assert Environment.from_string("prod") == Environment.PRODUCTION
        assert Environment.from_string("PROD") == Environment.PRODUCTION

    def test_from_string_none(self) -> None:
        """Test that passing None to from_string returns development environment."""
        assert Environment.from_string(None) == Environment.DEVELOPMENT

    def test_from_string_invalid(self) -> None:
        """Test that passing an invalid string to from_string raises ConfigError."""
        with pytest.raises(ConfigError) as excinfo:
            Environment.from_string("invalid")

        error = excinfo.value
        assert "Invalid environment: invalid" in str(error)
        assert error.code == "CONFIG_INVALID_ENVIRONMENT"
        assert error.context["provided_value"] == "invalid"

    def test_get_current(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test getting the current environment from environment variables."""
        # Test with UNO_ENV
        monkeypatch.setenv("UNO_ENV", "production")
        assert Environment.get_current() == Environment.PRODUCTION

        # Test with ENVIRONMENT
        monkeypatch.delenv("UNO_ENV")
        monkeypatch.setenv("ENVIRONMENT", "testing")
        assert Environment.get_current() == Environment.TESTING

        # Test with ENV
        monkeypatch.delenv("ENVIRONMENT")
        monkeypatch.setenv("ENV", "development")
        assert Environment.get_current() == Environment.DEVELOPMENT

        # Test default when no env vars are set
        monkeypatch.delenv("ENV")
        assert Environment.get_current() == Environment.DEVELOPMENT


class TestUnoSettings:
    """Tests for the UnoSettings base class."""

    class AppSettings(UnoSettings):
        """Test settings class."""

        app_name: str = "default_app"
        debug: bool = False
        port: int = 8000
        secret_key: str | None = None

    def test_basic_settings(self) -> None:
        """Test creating a settings object with default values."""
        settings = self.AppSettings()

        assert settings.app_name == "default_app"
        assert settings.debug is False
        assert settings.port == PORT_8000
        assert settings.secret_key is None

    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading settings from environment variables."""
        monkeypatch.setenv("APP_NAME", "test_app")
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("PORT", "5000")

        settings = self.AppSettings.from_env()

        assert settings.app_name == "test_app"
        assert settings.debug is True
        assert settings.port == PORT_5000

    def test_env_override(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test that environment variables override .env file values."""
        # Create a temporary .env file
        env_file = tmp_path / ".env"
        env_file.write_text("APP_NAME=file_app\nPORT=4000\n")

        # Set environment variables
        monkeypatch.setenv("APP_NAME", "env_app")

        # Change to the temporary directory
        cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Load settings
            settings = self.AppSettings()

            # Environment variables should take precedence
            assert settings.app_name == "env_app"
            # Other values should come from .env file
            assert settings.port == PORT_4000
        finally:
            os.chdir(cwd)


class TestEnvFileLoading:
    """Tests for .env file loading utilities."""

    def setup_env_files(self, tmp_path: Path) -> dict[str, Path]:
        """Set up test .env files in a temporary directory."""
        # Create base .env file
        base_env = tmp_path / ".env"
        base_env.write_text(
            "APP_NAME=base_app\n" "DEBUG=false\n" "PORT=8000\n" "BASE_ONLY=true\n"
        )

        # Create environment-specific .env file
        dev_env = tmp_path / ".env.development"
        dev_env.write_text("APP_NAME=dev_app\n" "DEBUG=true\n" "DEV_ONLY=true\n")

        # Create local override file
        local_env = tmp_path / ".env.local"
        local_env.write_text("APP_NAME=local_app\n" "LOCAL_ONLY=true\n")

        return {"base": base_env, "dev": dev_env, "local": local_env}

    def test_load_env_files(self, tmp_path: Path) -> None:
        """Test loading environment variables from .env files."""
        self.setup_env_files(tmp_path)

        # Change to the temporary directory
        cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Load environment files
            env_vars = load_env_files(Environment.DEVELOPMENT)

            # Values from higher priority files should override lower priority ones
            assert env_vars["APP_NAME"] == "local_app"  # From .env.local
            assert env_vars["DEBUG"] == "true"  # From .env.development
            assert env_vars["PORT"] == "8000"  # From .env
            assert env_vars["BASE_ONLY"] == "true"  # From .env
            assert env_vars["DEV_ONLY"] == "true"  # From .env.development
            assert env_vars["LOCAL_ONLY"] == "true"  # From .env.local
        finally:
            os.chdir(cwd)

    def test_get_env_value(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test getting a specific environment variable with .env fallbacks."""
        self.setup_env_files(tmp_path)

        # Change to the temporary directory
        cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Test environment variable takes precedence
            monkeypatch.setenv("APP_NAME", "env_app")
            assert get_env_value("APP_NAME") == "env_app"

            # Test fallback to .env files
            assert get_env_value("DEBUG") == "true"
            assert get_env_value("UNKNOWN", "default") == "default"
        finally:
            os.chdir(cwd)

    def test_production_ignores_local(self, tmp_path: Path) -> None:
        """Test that production environment ignores .env.local file."""
        self.setup_env_files(tmp_path)

        # Change to the temporary directory
        cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Create a production .env file
            prod_env = tmp_path / ".env.production"
            prod_env.write_text("APP_NAME=prod_app\n" "DEBUG=false\n")

            # Load environment files for production
            env_vars = load_env_files(Environment.PRODUCTION)

            # .env.local should be ignored in production
            assert env_vars["APP_NAME"] == "prod_app"  # From .env.production
            assert "LOCAL_ONLY" not in env_vars
        finally:
            os.chdir(cwd)


class TestConfigIntegration:
    """Tests for the configuration system's public API functions."""

    class DatabaseSettings(UnoSettings):
        """Test database settings class."""

        host: str = "localhost"
        port: int = 5432
        username: str = "postgres"
        password: str | None = None
        database: str = "test_db"

    def test_load_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test the load_settings function."""
        monkeypatch.setenv("HOST", "db.example.com")
        monkeypatch.setenv("PORT", "5433")

        settings = load_settings(self.DatabaseSettings)

        assert settings.host == "db.example.com"
        assert settings.port == PORT_5433
        assert settings.username == "postgres"  # Default value

    def test_get_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test the get_config function."""
        monkeypatch.setenv("DATABASE", "prod_db")

        settings = get_config(self.DatabaseSettings)

        assert settings.database == "prod_db"
