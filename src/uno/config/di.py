"""
Dependency injection integration for secure configuration.

This module provides integration between the DI container system and
the configuration system with secure value handling.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Generic, Protocol, Type, TypeVar

from uno.config import (
    SecureField,
    SecureValue,
    SecureValueHandling,
    UnoSettings,
    requires_secure_access,
)

T = TypeVar("T", bound=UnoSettings)


class ConfigProvider(Generic[T]):
    """Provider for configuration settings with secure value handling.

    This class wraps configuration settings and controls access to secure
    values, providing logging and access control capabilities.
    """

    def __init__(self, settings: T, logger: logging.Logger | None = None):
        """Initialize the config provider.

        Args:
            settings: The configuration settings to provide
            logger: Optional logger for auditing access
        """
        self._settings = settings
        self._logger = logger or logging.getLogger("uno.config")

    def get_settings(self) -> T:
        """Get the wrapped settings object.

        Note that secure values will still be protected and require
        explicit access through their get_value() methods.

        Returns:
            Settings object with secure values protected
        """
        return self._settings

    @requires_secure_access
    def get_secure_value(self, field_name: str) -> Any:
        """Get the value of a secure field.

        This method logs access and provides a controlled path to
        secure values. It should be used by services instead of
        accessing secure values directly.

        Args:
            field_name: Name of the field to access

        Returns:
            Unwrapped value of the secure field

        Raises:
            AttributeError: If the field doesn't exist
            SecureValueError: If field is sealed or access is denied
        """
        if not hasattr(self._settings, field_name):
            raise AttributeError(f"No config field named '{field_name}'")

        value = getattr(self._settings, field_name)

        # If it's a secure value, log access and unwrap
        if isinstance(value, SecureValue):
            self._logger.info(f"Secure config value accessed: {field_name}")
            return value.get_value()

        # Regular value, just return it
        return value


# Protocol definition for ConfigProvider registration in DI container
class ConfigProviderProtocol(Protocol[T]):
    """Protocol for config providers used in dependency injection."""

    def get_settings(self) -> T:
        """Get the wrapped settings object."""
        ...

    def get_secure_value(self, field_name: str) -> Any:
        """Get the value of a secure field."""
        ...


def register_secure_config(
    container: Any,  # Actual type would be Container from DI module
    settings_class: Type[T],
    lifetime: str = "singleton",
) -> None:
    """Register secure configuration with the DI container.

    This function creates and registers a ConfigProvider for the given
    settings class, making it available for injection into services.

    Args:
        container: The DI container to register with
        settings_class: Settings class to create config for
        lifetime: Service lifetime ("singleton", "scoped", or "transient")
    """

    # Factory function to create the config provider
    def create_config_provider() -> ConfigProvider[T]:
        # Get a logger from the container if available
        logger = None
        try:
            logger = container.resolve(logging.Logger)
        except Exception:
            # Fall back to default logger
            logger = logging.getLogger("uno.config")

        # Create settings instance
        settings = settings_class.from_env()

        # Create and return provider
        return ConfigProvider(settings, logger)

    # Register the provider with the container
    container.register(
        ConfigProviderProtocol[settings_class],
        factory=create_config_provider,
        lifetime=lifetime,
    )

    # Also register the concrete provider type for use cases that need the specific type
    container.register(
        ConfigProvider[settings_class],
        factory=create_config_provider,
        lifetime=lifetime,
    )
