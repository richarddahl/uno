"""Fixtures for configuration system tests."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Generator

import pytest
from cryptography.fernet import Fernet
from pydantic import Field

from uno.config import (
    Environment,
    SecureField,
    SecureValue,
    SecureValueHandling,
    Config,
)
from uno.config.secure import _secure_config_initialized
from uno.injection.protocols import ContainerProtocol

# Ensure all error codes are registered for tests
import uno.errors.base
import uno.config.errors


class MockContainer:
    """Simple mock container for testing."""

    def __init__(self) -> None:
        self.registered: dict[type, object] = {}

    def register_singleton(self, service_type: type, factory: object) -> None:
        """Register a singleton service."""
        if callable(factory) and not isinstance(factory, type):
            result = factory(self)
            self.registered[service_type] = result
        else:
            self.registered[service_type] = factory

    def resolve(self, service_type: type) -> object:
        """Resolve a service."""
        return self.registered.get(service_type)


@pytest.fixture
def test_encryption_key() -> bytes:
    """Generate a test encryption key."""
    return Fernet.generate_key()


@pytest.fixture
async def setup_secure_config(test_encryption_key: bytes) -> None:
    """Set up secure configuration for testing."""
    from uno.config import setup_secure_config as _setup_secure_config

    global _secure_config_initialized
    _secure_config_initialized = False
    SecureValue._encryption_keys.clear()
    SecureValue._current_key_version = None

    await _setup_secure_config(test_encryption_key.decode("utf-8"))

    yield

    _secure_config_initialized = False
    SecureValue._encryption_keys.clear()
    SecureValue._current_key_version = None


@pytest.fixture
def mock_container() -> MockContainer:
    """Create a mock container."""
    return MockContainer()


@pytest.fixture
def temp_env_files() -> Generator[tuple[Path, Path, Path], None, None]:
    """Create temporary .env files for testing.

    Returns:
        Tuple of (base_env, env_specific, local_env) Path objects
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_env = Path(tmp_dir) / ".env"
        with open(base_env, "w") as f:
            f.write("BASE_SETTING=base_value\n")
            f.write("OVERRIDE_SETTING=base_override\n")

        env_specific = Path(tmp_dir) / ".env.development"
        with open(env_specific, "w") as f:
            f.write("DEV_SETTING=dev_value\n")
            f.write("OVERRIDE_SETTING=dev_override\n")

        local_env = Path(tmp_dir) / ".env.local"
        with open(local_env, "w") as f:
            f.write("LOCAL_SETTING=local_value\n")
            f.write("OVERRIDE_SETTING=local_override\n")

        old_cwd = os.getcwd()
        os.chdir(tmp_dir)
        try:
            yield base_env, env_specific, local_env
        finally:
            os.chdir(old_cwd)


@pytest.fixture
def env_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for environment files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        old_cwd = os.getcwd()
        os.chdir(temp_path)
        yield temp_path
        os.chdir(old_cwd)


@pytest.fixture
def save_env_vars() -> Generator[None, None, None]:
    """Save and restore environment variables."""
    saved_vars = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(saved_vars)


@pytest.fixture
def clear_config_cache() -> Generator[None, None, None]:
    """Clear the configuration cache before and after test."""
    from uno.config.settings import CONFIG_CACHE
    from uno.config.env_cache import env_cache

    CONFIG_CACHE.clear()
    env_cache.clear()
    yield
    CONFIG_CACHE.clear()
    env_cache.clear()


class BasicSettings(Config):
    """Basic settings class for tests."""

    __test__ = False

    app_name: str = "test_app"
    debug: bool = False
    port: int = 8000


class SecureSettings(Config):
    """Settings with secure fields for testing."""

    __test__ = False

    username: str = "admin"
    password: Any = SecureField("s3cret", handling=SecureValueHandling.MASK)
    api_key: Any = SecureField("abc123", handling=SecureValueHandling.ENCRYPT)
    token: Any = SecureField("token123", handling=SecureValueHandling.SEALED)


class NestedSettings(Config):
    """Settings with nested config for testing."""

    __test__ = False

    name: str = "nested_app"
    basic: BasicSettings = Field(default_factory=BasicSettings)
    secure: SecureSettings = Field(default_factory=SecureSettings)


@pytest.fixture
def basic_settings() -> BasicSettings:
    """Return a BasicSettings instance."""
    return BasicSettings()


@pytest.fixture
def secure_settings(setup_secure_config: None) -> SecureSettings:
    """Return a SecureSettings instance with secure config set up."""
    return SecureSettings()


@pytest.fixture
def nested_settings(setup_secure_config: None) -> NestedSettings:
    """Return a NestedSettings instance with secure config set up."""
    return NestedSettings()


@pytest.fixture
async def secure_value_helper() -> Callable[[SecureValue[Any], Any], None]:
    """Return a helper function to test secure values."""

    async def helper(secure_value: SecureValue[Any], expected_value: Any) -> None:
        assert await secure_value.get_value() == expected_value

    return helper
