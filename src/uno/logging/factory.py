"""
Logger factory implementation for dependency injection.

This module provides a factory for creating loggers that are properly configured and
scoped according to the application's needs.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from uno.logging.config import LoggingSettings
from uno.logging.logger import get_logger

if TYPE_CHECKING:
    from uno.di.protocols import ContainerProtocol
    from uno.logging.protocols import LoggerProtocol


@runtime_checkable
class LoggerFactoryProtocol(Protocol):
    """Protocol for logger factory implementations."""

    async def create_logger(self, name: str) -> LoggerProtocol:
        """Create a new logger instance."""
        ...

    @asynccontextmanager
    async def scoped_logger(self, name: str) -> AsyncIterator[LoggerProtocol]:
        """Create a scoped logger instance."""
        ...


class LoggerFactory(LoggerFactoryProtocol):
    """Logger factory implementation that integrates with Uno's dependency injection system."""

    def __init__(self, container: ContainerProtocol, settings: LoggingSettings) -> None:
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


def register_logger_factory(
    container: ContainerProtocol, settings: LoggingSettings
) -> None:
    """
    Register the logger factory with the dependency injection container.

    Args:
        container: The dependency injection container.
        settings: The logging configuration settings.
    """
    factory = LoggerFactory(container, settings)
    container.register_singleton(LoggerFactoryProtocol, factory)
