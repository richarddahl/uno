"""
Logger factory implementation for dependency injection.

This module provides a factory for creating loggers that are properly configured and
scoped according to the application's needs.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING
import asyncio

from uno.logging.config import LoggingSettings
from uno.logging.logger import get_logger

if TYPE_CHECKING:
    from uno.logging.protocols import LoggerFactoryProtocol, LoggerProtocol

if TYPE_CHECKING:
    from uno.di.protocols import ContainerProtocol


class LoggerFactory:
    """
    Logger factory for Uno DI system.

    Usage:
        - Register with DI using register_logger_factory(container, settings).
        - Use create_logger(name) to get a logger instance (async).
        - Use scoped_logger(name) as an async context manager for per-scope loggers.

    Lifecycle:
        - LoggerFactory is a singleton in the DI container.
        - Logger instances are created on demand and are not reused unless cached externally.
        - scoped_logger provides a context-managed logger, ensuring cleanup hooks are called (currently a no-op, but contract is enforced).

    Resource Cleanup:
        - The scoped_logger context manager ensures any future cleanup logic is executed.
        - Even if currently a no-op, always use the context manager for scoped loggers.
    """

    def __init__(
        self, container: "ContainerProtocol", settings: LoggingSettings
    ) -> None:
        """Initialize the logger factory."""
        self.container = container
        self.settings = settings

    async def create_logger(self, name: str) -> LoggerProtocol:
        """
        Create a new logger instance.

        Args:
            name: The name of the logger to create.

        Returns:
            A configured logger instance.
        """
        return get_logger(name)

    @asynccontextmanager
    async def scoped_logger(self, name: str) -> AsyncIterator[LoggerProtocol]:
        """
        Create a scoped logger instance that will be automatically cleaned up.

        Args:
            name: The name of the logger to create.

        Yields:
            A scoped logger instance.
        """
        logger = await self.create_logger(name)
        try:
            yield logger
        finally:
            # Clean up any scoped resources
            pass  # Currently no cleanup needed, but placeholder for future needs


async def register_logger_factory(
    container: "ContainerProtocol", settings: LoggingSettings
) -> None:
    """
    Register LoggerFactory as a singleton in the DI container.

    Usage:
        - Call this during DI setup to make LoggerFactory available everywhere via LoggerFactoryProtocol.
        - Ensures all loggers are configured using the provided settings.

    Args:
        container: The dependency injection container.
        settings: The logging configuration settings.
    """
    factory = LoggerFactory(container, settings)
    from uno.logging.protocols import LoggerFactoryProtocol  # avoid circular import

    if not isinstance(factory, LoggerFactoryProtocol):
        raise TypeError(
            "LoggerFactory does not structurally implement LoggerFactoryProtocol"
        )

    async def factory_provider(_: ContainerProtocol) -> LoggerFactory:
        return factory

    await container.register_singleton(LoggerFactoryProtocol, factory_provider)
