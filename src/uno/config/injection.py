# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Integration extension for Uno configuration system: DI registration helpers.
"""

from typing import Any, cast
from uno.types import T

from uno.config.protocols import ConfigProtocol
from uno.injection.protocols import ContainerProtocol


class ConfigRegistrationExtensions:
    """
    Extension methods for registering configuration objects with the DI container.
    """

    @staticmethod
    def register_configuration(container: ContainerProtocol, config: T) -> None:
        """
        Register the configuration object as a singleton in the DI container.

        Args:
            container: The DI container
            config: The configuration object to register
        """
        # Store concrete type for later use
        config_type = type(config)

        # Create factory function that always returns the same instance
        def config_factory(_: Any) -> T:
            return config

        # Register under concrete type with the highest priority
        container.register_singleton(config_type, config_factory)

        # Register with ConfigProtocol (for interface-based resolution)
        def protocol_factory(_: Any) -> ConfigProtocol:
            return cast(ConfigProtocol, config)

        container.register_singleton(ConfigProtocol, protocol_factory)
