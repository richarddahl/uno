"""
Factory for creating logger instances used in the event sourcing system.

This module provides factory classes for creating loggers using Uno's DI system,
enabling better testability and configuration management.
"""

from collections.abc import Callable
from typing import Optional

from uno.core.di.container import DIContainer
from uno.core.di.providers import Factory, Provider
from uno.core.logging.logger import LoggerService


class LoggerServiceFactory(Factory[LoggerService]):
    """Factory for creating LoggerService instances."""
    
    def __init__(self, base_name: str = "uno.events"):
        """
        Initialize the factory with a base logger name.
        
        Args:
            base_name: The base name for loggers created by this factory
        """
        self.base_name = base_name
        
    def __call__(self, component_name: str | None = None) -> LoggerService:
        """
        Create a new LoggerService instance.
        
        Args:
            component_name: Optional component name to append to the base name
            
        Returns:
            A configured LoggerService instance
        """
        logger_name = self.base_name
        if component_name:
            logger_name = f"{self.base_name}.{component_name}"
            
        return LoggerService(name=logger_name)


def register_event_logging_factories(container: DIContainer) -> None:
    """
    Register all event-related logging factories with the DI container.
    
    Args:
        container: The DI container to register with
    """
    # Register the base factory
    container.register(
        "event_logger_factory", 
        Provider(LoggerServiceFactory)
    )
    
    # Register specific logger factories
    container.register(
        "event_store_logger_factory",
        Provider(LoggerServiceFactory, base_name="uno.events.store")
    )
    
    container.register(
        "event_repository_logger_factory",
        Provider(LoggerServiceFactory, base_name="uno.events.repository")
    )
    
    container.register(
        "event_snapshot_logger_factory",
        Provider(LoggerServiceFactory, base_name="uno.events.snapshots")
    )


def get_logger_for_component(
    container: DIContainer, 
    factory_name: str = "event_logger_factory",
    component_name: str | None = None
) -> LoggerService:
    """
    Get a logger for a specific component from the DI container.
    
    Args:
        container: The DI container
        factory_name: Name of the logger factory to use
        component_name: Optional component name to append to the logger name
        
    Returns:
        A configured LoggerService instance
    """
    factory: Callable[..., LoggerService] = container.resolve(factory_name)
    return factory(component_name)
