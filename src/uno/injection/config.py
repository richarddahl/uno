# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework

"""
Dependency injection integration for secure configuration.

This module provides integration between the DI container system and
the configuration system with secure value handling.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Generic, TypeVar, Optional

from uno.config import (
    SecureValue,
    UnoSettings,
    requires_secure_access,
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uno.injection.protocols import ContainerProtocol

T = TypeVar("T", bound=UnoSettings)


class ServiceLifetime(str, Enum):
    """Service lifetime options for dependency injection."""

    SINGLETON = "singleton"
    SCOPED = "scoped"
    TRANSIENT = "transient"


class ConfigProvider(Generic[T]):
    """Provider for configuration settings with secure value handling.

    This class wraps configuration settings and controls access to secure
    values, providing logging and access control capabilities.
    """

    def __init__(self, settings: T, logger: Optional[logging.Logger] = None):
        """Initialize the config provider.

        Args:
            settings: The configuration settings to provide
            logger: Optional logger for auditing access
        """
        self._settings = settings
        if logger is not None:
            self._logger = logger
        else:
            # Fallback: should only occur if DI failed to provide a logger
            fallback_logger = logging.getLogger("uno.config")
            fallback_logger.debug(
                "Falling back to direct logger instantiation in ConfigProvider"
            )
            self._logger = fallback_logger

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


async def register_secure_config(
    container: "ContainerProtocol",
    settings_class: type[T],
    lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
) -> ConfigProvider[T]:
    """Register secure configuration with the DI container.

    This function creates and registers a ConfigProvider for the given
    settings class, making it available for injection into services.

    Args:
        container: The DI container to register with
        settings_class: Settings class to create config for
        lifetime: Service lifetime ("singleton", "scoped", or "transient")

    Returns:
        The created ConfigProvider instance

    Raises:
        ValueError: If an invalid lifetime is provided
    """
    # Create settings instance synchronously
    # If settings_class.from_env() could be async, this would need to be handled differently
    settings = settings_class.from_env()

    # Get a logger from the container if available
    async def resolve_logger(container, name: str = "uno.config") -> logging.Logger:
        try:
            logger = await container.resolve(logging.Logger)
            if logger is not None:
                return logger
        except Exception as e:
            fallback_logger = logging.getLogger(name)
            fallback_logger.debug(
                f"Falling back to direct logger instantiation in register_secure_config: {e}"
            )
            return fallback_logger
        return logging.getLogger(name)

    logger = await resolve_logger(container, "uno.config")

    # Create provider
    provider = ConfigProvider(settings, logger)

    # Register the provider with the container
    if lifetime == ServiceLifetime.SINGLETON:
        await container.register_singleton(
            ConfigProvider[settings_class], provider, replace=True
        )
    elif lifetime == ServiceLifetime.SCOPED:
        await container.register_scoped(
            ConfigProvider[settings_class], provider, replace=True
        )
    elif lifetime == ServiceLifetime.TRANSIENT:
        await container.register_transient(
            ConfigProvider[settings_class], provider, replace=True
        )
    else:
        raise ValueError(
            f"Invalid lifetime: {lifetime}. Expected one of: {', '.join(t.value for t in ServiceLifetime)}"
        )

    # Also register with the concrete type name for convenience
    container_type_name = settings_class.__name__ + "Provider"
    await container.register_type_name(
        container_type_name, ConfigProvider[settings_class]
    )

    return provider
