"""
Logger service factory for creating logger instances.

This module provides a factory for creating LoggerService instances
with consistent configuration and naming.
"""

from collections.abc import Callable
from typing import Protocol

from uno.infrastructure.logging.logger import LoggerService, LoggingConfig


class LoggerServiceFactory(Protocol):
    """Protocol for a factory that creates logger services."""

    def create(self, component_name: str) -> LoggerService:
        """
        Create a new LoggerService for a component.

        Args:
            component_name: Name of the component requesting the logger

        Returns:
            A configured LoggerService instance
        """
        ...


class DefaultLoggerServiceFactory:
    """Default implementation of LoggerServiceFactory."""

    def __init__(self, base_namespace: str = "uno"):
        """
        Initialize the factory.

        Args:
            base_namespace: Base namespace for all loggers
        """
        self.base_namespace = base_namespace

    def create(self, component_name: str) -> LoggerService:
        """
        Create a new LoggerService for a component.

        Args:
            component_name: Name of the component requesting the logger

        Returns:
            A configured LoggerService instance
        """
        logger_name = f"{self.base_namespace}.{component_name}"
        # NOTE: LoggerService no longer takes a name argument. Use LoggingConfig().
        return LoggerService(LoggingConfig())


def create_logger_factory(base_namespace: str = "uno") -> LoggerServiceFactory:
    """
    Create a new DefaultLoggerServiceFactory.

    Args:
        base_namespace: Base namespace for all loggers

    Returns:
        A configured LoggerServiceFactory instance
    """
    return DefaultLoggerServiceFactory(base_namespace=base_namespace)


# Factory for creating logger services with a specific namespace
LoggerFactoryCallable = Callable[[str], LoggerService]


def create_logger_factory_callable(
    base_namespace: str = "uno",
) -> LoggerFactoryCallable:
    """
    Create a callable factory for creating logger services.

    This is a simplified version that returns a callable function
    instead of a full factory object, for backward compatibility.

    Args:
        base_namespace: Base namespace for all loggers

    Returns:
        A callable that creates logger services
    """
    factory = DefaultLoggerServiceFactory(base_namespace=base_namespace)
    return factory.create
