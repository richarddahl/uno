"""Fixtures for configuration system tests."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
from cryptography.fernet import Fernet

from uno.config import Environment, SecureValue, UnoSettings
from uno.config.base import UnoSettings
from uno.di.protocols import ContainerProtocol


class MockContainer:
    """Simple mock container for testing."""

    def __init__(self) -> None:
        self.registered: dict[type, object] = {}

    async def register_singleton(self, service_type: type, factory: object) -> None:
        """Register a singleton service."""
        if callable(factory) and not isinstance(factory, type):
            # If factory is a lambda/function, call it with self
            # Check if it's awaitable or not
            result = factory(self)
            if hasattr(result, "__await__"):
                # If awaitable, await it
                self.registered[service_type] = await result
            else:
                # Non-awaitable factory
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
    from uno.config import setup_secure_config

    await setup_secure_config(test_encryption_key)


@pytest.fixture
def mock_container() -> MockContainer:
    """Create a mock container."""
    return MockContainer()


@pytest.fixture
def temp_env_files() -> Generator[tuple[Path, Path, Path], None, None]:
    """Create temporary .env files for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create base .env file
        base_env = Path(tmp_dir) / ".env"
        with open(base_env, "w") as f:
            f.write("BASE_SETTING=base_value\n")
            f.write("OVERRIDE_SETTING=base_override\n")

        # Create environment-specific .env file
        env_specific = Path(tmp_dir) / ".env.development"
        with open(env_specific, "w") as f:
            f.write("DEV_SETTING=dev_value\n")
            f.write("OVERRIDE_SETTING=dev_override\n")

        # Create local override .env file
        local_env = Path(tmp_dir) / ".env.local"
        with open(local_env, "w") as f:
            f.write("LOCAL_SETTING=local_value\n")
            f.write("OVERRIDE_SETTING=local_override\n")

        # Change working directory to temp directory for test
        old_cwd = os.getcwd()
        os.chdir(tmp_dir)

        try:
            yield base_env, env_specific, local_env
        finally:
            # Restore original working directory
            os.chdir(old_cwd)


@pytest.fixture
def clear_config_cache() -> Generator[None, None, None]:
    """Clear the configuration cache before and after test."""
    from uno.config import _config_cache

    _config_cache.clear()
    yield
    _config_cache.clear()


class TestSettings(UnoSettings):
    """Test settings class."""

    __test__ = False

    app_name: str = "test_app"
    debug: bool = False
    port: int = 8000
    connection_string: str | None = None


@pytest.fixture
def test_settings_class() -> type[TestSettings]:
    """Return a test settings class."""
    return TestSettings
