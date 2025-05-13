"""Tests for async API consistency."""

from __future__ import annotations

import asyncio
import os
from typing import Any, ClassVar

import pytest

from uno.config import (
    Environment,
    SecureField,
    SecureValueHandling,
    UnoSettings,
    get_config,
    load_settings,
    setup_secure_config,
)
from uno.config.di import ConfigRegistrationExtensions


class TestSettings(UnoSettings):
    """Test settings class."""

    __test__ = False  # Prevent pytest from treating this as a test case

    app_name: str = "test_app"
    debug: bool = False
    api_key: str = SecureField("test_key", handling=SecureValueHandling.MASK)
    # Instance-level secure fields
    _secure_fields: ClassVar[dict[str, SecureValueHandling]] = {}


class TestAsyncAPI:
    """Test async API consistency."""

    async def test_load_settings(self, setup_secure_config: None, monkeypatch) -> None:
        """Test async load_settings function."""
        # Ensure API_KEY is set to test value for isolation
        monkeypatch.setenv("API_KEY", "test_key")
        # Clear any other possible interfering variables
        monkeypatch.delenv("TEST_API_KEY", raising=False)
        monkeypatch.delenv("TEST_SETTINGS__API_KEY", raising=False)

        # Should be properly async
        settings = await load_settings(TestSettings)

        assert settings.app_name == "test_app"
        assert settings.debug is False
        assert settings.api_key == "test_key"

    async def test_get_config(
        self, setup_secure_config: None, clear_config_cache: None
    ) -> None:
        """Test async get_config function with caching."""
        # First call should load settings
        settings1 = await get_config(TestSettings)
        assert settings1.app_name == "test_app"

        # Second call should return cached instance
        settings2 = await get_config(TestSettings)
        assert settings2 is settings1  # Same instance

    async def test_thread_safe_caching(
        self, setup_secure_config: None, clear_config_cache: None
    ) -> None:
        """Test thread-safe caching for get_config."""

        # Define multiple settings classes
        class Settings1(UnoSettings):
            name: str = "settings1"

        class Settings2(UnoSettings):
            name: str = "settings2"

        # Create multiple concurrent tasks
        async def load_both() -> tuple[UnoSettings, UnoSettings]:
            # Load both settings classes concurrently
            s1_task = asyncio.create_task(get_config(Settings1))
            s2_task = asyncio.create_task(get_config(Settings2))
            return await s1_task, await s2_task

        # Run multiple instances of the concurrent loading
        tasks = [asyncio.create_task(load_both()) for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # All instances of Settings1 should be the same object
        settings1_instances = [result[0] for result in results]
        assert all(
            instance is settings1_instances[0] for instance in settings1_instances
        )

        # All instances of Settings2 should be the same object
        settings2_instances = [result[1] for result in results]
        assert all(
            instance is settings2_instances[0] for instance in settings2_instances
        )

        # But Settings1 and Settings2 should be different objects
        assert settings1_instances[0] is not settings2_instances[0]

    async def test_setup_secure_config(self, test_encryption_key: bytes) -> None:
        """Test async setup_secure_config function."""
        # Clear any existing setup
        from uno.config.secure import SecureValue

        SecureValue._encryption_key = None

        # Should be properly async
        await setup_secure_config(test_encryption_key)

        # Key should be set
        assert SecureValue._encryption_key is not None

    async def test_di_registration(
        self, mock_container: Any, setup_secure_config: None
    ) -> None:
        """Test DI container registration."""
        # Create settings
        settings = TestSettings()

        # Register with container
        await ConfigRegistrationExtensions.register_configuration(
            mock_container, settings
        )

        # Check registration
        resolved = mock_container.resolve(UnoSettings)
        assert resolved is settings
