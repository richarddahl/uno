"""
Dependency injection registration extensions for Uno's logging system.

This module provides extension methods for registering logging-related components
with the dependency injection container.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from uno.di.protocols import ContainerProtocol
from uno.logging.config import LoggingSettings
from uno.logging.factory import register_logger_factory
from uno.logging.logger import get_logger

if TYPE_CHECKING:
    from uno.logging.protocols import LoggerProtocol


class LoggingRegistrationExtensions:
    """Extension methods for registering logging components."""

    @staticmethod
    async def register_logging(
        container: ContainerProtocol,
        settings: LoggingSettings | None = None,
    ) -> None:
        """
        Register all logging components with the container.

        Args:
            container: The dependency injection container.
            settings: Optional logging settings. If not provided, will use default settings.
        """
        if settings is None:
            settings = LoggingSettings.load()

        # Register logger factory
        await register_logger_factory(container, settings)

    @staticmethod
    def register_logger(
        container: ContainerProtocol,
        name: str,
    ) -> LoggerProtocol:
        """
        Register a named logger with the container.

        Args:
            container: The dependency injection container.
            name: The name of the logger to register.

        Returns:
            The registered logger instance.
        """
        logger = get_logger(name)
        container.register_singleton(LoggerProtocol, logger)
        return logger
