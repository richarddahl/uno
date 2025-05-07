# SPDX-FileCopyrightT_coext: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT_co
# uno framework
"""
Scoped dependency injection container for Uno framework.

This module provides the core container functionality for the DI system.
It defines the ServiceFactoryProtocol for creating service instances.

Note: All dependencies must be passed explicitly from the composition root.

Public API:
- ServiceCollection: Main API for registering services
- ServiceScope: Enum for service lifetimes
- ServiceFactoryProtocol: Protocol for service factories

Internal/advanced classes (ServiceRegistration, _ServiceResolver) are not part of the public API.
"""

from typing import Any, Protocol, TypeVar, Callable, runtime_checkable

# Type variables
TService = TypeVar("TService", bound=Any)
TImplementation = TypeVar("TImplementation", bound=Any)
TFactory = TypeVar("TFactory", bound=Callable[..., Any])

@runtime_checkable
class ServiceFactoryProtocol(Protocol[TService]):
    """
    Protocol for service factories.

    This protocol defines the interface for creating service instances.
    Factories are used to create service instances with custom initialization.

    Note: All dependencies must be passed explicitly from the composition root.

    Example:
        ```python
        class MyServiceFactory(ServiceFactoryProtocol[MyService]):
            def __call__(self, *args: Any, **kwargs: Any) -> MyService:
                # Create and initialize service
                return MyService(*args, **kwargs)
        ```
    """

    def __call__(self, *args: Any, **kwargs: Any) -> TService:
        """
        Create a service instance.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            The created service instance

        Example:
            ```python
            # Create a service instance
            factory = MyServiceFactory()
            service = factory(arg1, arg2, kwarg1=value1)
            ```
        """
        ...
