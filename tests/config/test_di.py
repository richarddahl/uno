"""
Unit tests for Uno configuration DI integration.

This module contains focused unit tests for the ConfigRegistrationExtensions class,
verifying its behavior in isolation from the integration tests.
"""

import pytest
from unittest.mock import MagicMock
from uno.config import UnoSettings
from uno.config.di import ConfigRegistrationExtensions
from uno.di import ContainerProtocol


class TestConfigRegistrationExtensions:
    """Tests for ConfigRegistrationExtensions class."""

    def test_register_configuration(self, mocker) -> None:
        """Test that register_configuration correctly registers a config object."""
        # Mock the container
        mock_container = MagicMock(spec=ContainerProtocol)
        mock_container.register_singleton = MagicMock()

        # Create a test settings class
        class TestSettings(UnoSettings):
            foo: str = "bar"

        # Create an instance of the settings
        settings = TestSettings()

        # Call the method
        ConfigRegistrationExtensions.register_configuration(mock_container, settings)

        # Verify the container's register_singleton was called correctly
        mock_container.register_singleton.assert_called_once_with(UnoSettings, settings)

    def test_register_configuration_type_safety(self) -> None:
        """Test that register_configuration enforces UnoSettings type."""
        # Mock the container
        container = MagicMock()
        container.register_singleton = MagicMock()

        # Create a non-UnoSettings class
        class NotSettings:
            pass

        # Create an instance
        not_settings = NotSettings()

        # This should be caught by type checking (not runtime)
        with pytest.raises(TypeError):
            ConfigRegistrationExtensions.register_configuration(
                container, not_settings  # type: ignore
            )

    def test_register_configuration_with_none(self) -> None:
        """Test that register_configuration handles None values correctly."""
        # Mock the container
        mock_container = MagicMock(spec=ContainerProtocol)
        mock_container.register_singleton = MagicMock()

        # Create a test settings class
        class TestSettings(UnoSettings):
            foo: str = "bar"

        # Provide all required fields for TestSettings
        with pytest.raises(ValidationError):
            TestSettings(foo=None)  # type: ignore

    def test_register_configuration_with_env_specific(self) -> None:
        """Test that register_configuration preserves environment-specific values."""
        # Mock the container
        container = MagicMock()
        container.register_singleton = MagicMock()

        # Create a test settings class
        class TestSettings(UnoSettings):
            env_specific: str = "default"

        # Create an instance with environment-specific value
        settings = TestSettings(env_specific="test")

        # Call the method
        ConfigRegistrationExtensions.register_configuration(container, settings)

        # Verify the container's register_singleton was called correctly
        container.register_singleton.assert_called_once_with(UnoSettings, settings)
        # Verify the environment-specific value was preserved
        assert settings.env_specific == "test"
