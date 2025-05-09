"""
Protocol definitions for the uno DI system.

This module contains the core protocols that define the interface for the DI container and its components.
"""

from typing import Literal, Protocol, runtime_checkable

from uno.di.registration import ServiceRegistration
from uno.di.shared_types import ContainerProtocol, T_co
from uno.di.types import (
    AsyncServiceFactoryProtocol,
    ServiceFactoryProtocol,
    T,
)


@runtime_checkable
class ScopeProtocol(Protocol):
    """Protocol for a DI scope."""

    async def resolve(self, interface: type[T]) -> T:
        """Resolve a service within this scope."""
        ...

    def __getitem__(self, key: type[T]) -> T:
        """Get a service by type."""
        ...

    def __setitem__(self, key: type[T], value: T) -> None:
        """Set a service by type."""
        ...

    async def dispose(self) -> None:
        """Dispose of the scope and its services."""
        ...

    def create_scope(self) -> "ScopeProtocol":
        """Create a child scope."""
        ...


@runtime_checkable
class ServiceProtocol(Protocol):
    """Protocol for a service."""

    ...


@runtime_checkable
class ServiceRegistrationProtocol(Protocol[T]):
    """Protocol for service registration."""

    interface: type[T]
    implementation: type[T] | ServiceFactoryProtocol[T] | AsyncServiceFactoryProtocol[T]
    lifetime: Literal["singleton", "scoped", "transient"]

    def __init__(
        self,
        interface: type[T],
        implementation: (
            type[T] | ServiceFactoryProtocol[T] | AsyncServiceFactoryProtocol[T]
        ),
        lifetime: Literal["singleton", "scoped", "transient"],
    ) -> None:
        """Initialize a service registration."""
        ...

    def __eq__(self, other: object) -> bool:
        """Compare service registrations."""
        ...

    def __hash__(self) -> int:
        """Hash a service registration."""
        ...

    def __repr__(self) -> str:
        """Represent a service registration as a string."""
        ...
