"""
Integration extension for Uno configuration system: DI registration helpers.
"""

from typing import Any, Callable
from uno.types import T

from uno.config import UnoSettings
from uno.di.protocols import ContainerProtocol



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

        # Create non-awaitable factory functions that simply return the config
        # This works with both async and sync containers
        def config_factory(_: Any) -> T:
            return config

        # Register with specific type and base UnoSettings type
        container.register_singleton(type(config), config_factory)
        container.register_singleton(UnoSettings, config_factory)
