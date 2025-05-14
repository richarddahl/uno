"""
Service registration module for uno DI container.

This module defines the ServiceRegistration class used to track service registrations
in the DI container.
"""

from __future__ import annotations

import asyncio
from typing import Any, TypeVar, Generic
from uno.di.protocols import AsyncServiceFactoryProtocol, ServiceFactoryProtocol
from uno.di.config import ServiceLifetime
from uno.di.lifetime_policies import LIFETIME_POLICY_MAP

T = TypeVar("T")

class ServiceRegistration(Generic[T]):
    """Represents a service registration in the DI container.

    A registration contains the interface type, its implementation or factory,
    and the lifetime scope for the service.
    """

    def __init__(
        self,
        interface: type[T],
        implementation: (
            type[T] | ServiceFactoryProtocol[T] | AsyncServiceFactoryProtocol[T]
        ),
        lifetime: ServiceLifetime,
    ) -> None:
        """Initialize a service registration.

        Args:
            interface: The interface type that will be used to resolve the service
            implementation: Either a concrete type, or a factory function that creates instances
            lifetime: The lifetime of the service (ServiceLifetime)
        """
        self.interface = interface
        self.implementation = implementation
        self.lifetime = lifetime
        self.lifetime_policy = LIFETIME_POLICY_MAP[lifetime]

    @property
    def is_factory(self) -> bool:
        """Check if the implementation is a factory rather than a concrete type.

        Returns:
            bool: True if implementation is a factory function, False if it's a type
        """
        return not isinstance(self.implementation, type)

    @property
    def is_async_factory(self) -> bool:
        """Check if the implementation is an async factory.

        Returns:
            bool: True if implementation is an async factory function
        """
        if not self.is_factory:
            return False

        return asyncio.iscoroutinefunction(self.implementation)


async def register_logging_services(container: Any) -> None:
    """Register standard logging services with a container.

    This function registers the logging services (LoggerScopeProtocol,
    LoggerFactoryProtocol) with the provided container.

    Args:
        container: The DI container to register services with
    """
    try:
        # Import logging protocols and implementations
        from uno.logging.scope import LoggerScopeProtocol
        from uno.logging.factory import LoggerFactoryProtocol
        from uno.logging.scope import LoggerScope
        from uno.logging.factory import LoggerFactory

        # Register the logging services
        await container.register_singleton(LoggerScopeProtocol, LoggerScope)
        await container.register_singleton(LoggerFactoryProtocol, LoggerFactory)
    except ImportError as e:
        # Handle case where logging module may not be available
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to register logging services: {e}")
