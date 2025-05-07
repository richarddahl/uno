"""
Service lifecycle implementation for Uno DI.

This module provides utilities for managing service lifecycles in the DI container.
It includes helper functions for initialization and disposal of both sync and async services.

Note: All dependencies must be passed explicitly from the composition root.
"""

from __future__ import annotations

from typing import TypeVar, Any, Callable, Dict, List
from dataclasses import dataclass, field
from enum import Enum, auto

from uno.infrastructure.di.interfaces import ServiceLifecycleProtocol
from uno.infrastructure.di.errors import ServiceLifecycleError

# Type variables
TService = TypeVar("TService", bound=Any)
TImplementation = TypeVar("TImplementation", bound=Any)
TFactory = TypeVar("TFactory", bound=Callable[..., Any])


class ServiceState(Enum):
    """Service lifecycle states."""
    CREATED = auto()
    INITIALIZING = auto()
    INITIALIZED = auto()
    DISPOSING = auto()
    DISPOSED = auto()
    ERROR = auto()


@dataclass
class ServiceLifecycle:
    """
    Manages the lifecycle of a service.

    This class tracks the state of a service and provides methods for
    initialization and disposal.

    Example:
        ```python
        lifecycle = ServiceLifecycle(service)
        await lifecycle.initialize()
        try:
            # Use the service
            pass
        finally:
            await lifecycle.dispose()
        ```
    """
    service: ServiceLifecycleProtocol
    state: ServiceState = field(default=ServiceState.CREATED)
    error: Exception | None = field(default=None)
    dependencies: list[ServiceLifecycleProtocol] = field(default_factory=list)

    async def initialize(self) -> None:
        """
        Initialize the service.

        This method will:
        1. Initialize all dependencies
        2. Initialize the service itself
        3. Update the service state

        Raises:
            ServiceLifecycleError: If initialization fails
        """
        if self.state != ServiceState.CREATED:
            raise ServiceLifecycleError(
                f"Service is in {self.state} state, cannot initialize"
            )

        try:
            self.state = ServiceState.INITIALIZING

            # Initialize dependencies first
            for dep in self.dependencies:
                await dep.initialize()

            # Initialize the service
            await self.service.initialize()
            self.state = ServiceState.INITIALIZED

        except Exception as e:
            self.state = ServiceState.ERROR
            self.error = e
            raise ServiceLifecycleError(
                f"Failed to initialize service: {str(e)}"
            ) from e

    async def dispose(self) -> None:
        """
        Dispose of the service.

        This method will:
        1. Dispose of the service itself
        2. Dispose of all dependencies in reverse order
        3. Update the service state

        Raises:
            ServiceLifecycleError: If disposal fails
        """
        if self.state not in (ServiceState.INITIALIZED, ServiceState.ERROR):
            raise ServiceLifecycleError(
                f"Service is in {self.state} state, cannot dispose"
            )

        try:
            self.state = ServiceState.DISPOSING

            # Dispose of the service first
            await self.service.cleanup()

            # Dispose of dependencies in reverse order
            for dep in reversed(self.dependencies):
                await dep.dispose()

            self.state = ServiceState.DISPOSED

        except Exception as e:
            self.state = ServiceState.ERROR
            self.error = e
            raise ServiceLifecycleError(
                f"Failed to dispose service: {str(e)}"
            ) from e


async def initialize_service(service: ServiceLifecycleProtocol) -> None:
    """
    Initialize a service.

    Args:
        service: The service to initialize

    Note: This is a helper function for service initialization.

    Example:
        ```python
        # Initialize a service
        await initialize_service(my_service)
        ```
    """
    await service.initialize()


async def dispose_service(service: ServiceLifecycleProtocol) -> None:
    """
    Dispose of a service.

    Args:
        service: The service to dispose

    Note: This is a helper function for service disposal.

    Example:
        ```python
        # Dispose of a service
        await dispose_service(my_service)
        ```
    """
    await service.cleanup()


__all__ = [
    "initialize_service",
    "dispose_service",
    "TService",
    "TImplementation",
    "TFactory",
    "ServiceLifecycle",
    "ServiceState",
]
