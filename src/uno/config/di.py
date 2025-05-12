"""
Integration extension for Uno configuration system: DI registration helpers.
"""

from uno.config import UnoSettings
from uno.di.protocols import ContainerProtocol


class ConfigRegistrationExtensions:
    """
    Extension methods for registering configuration objects with the DI container.
    """

    @staticmethod
    def register_configuration(
        container: ContainerProtocol, config: UnoSettings
    ) -> None:
        """
        Register the configuration object as a singleton in the DI container.
        """
        container.register_singleton(UnoSettings, config)
