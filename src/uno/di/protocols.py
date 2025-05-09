"""
Protocol definitions for the uno DI system.

This module contains the core protocols that define the interface for the DI container and its components.
"""

from collections.abc import Awaitable, Callable
from typing import Any, Literal, Protocol, runtime_checkable

from uno.di.types import T, T_co


@runtime_checkable
class ContainerProtocol(Protocol):
    """Protocol for DI container."""

    _registrations: dict[type[Any], Any]
    _singleton_scope: Any

    async def resolve(self, service_type: type[T]) -> T: ...

    async def _dispose_service(self, service: T) -> None: ...

    async def _create_service(self, interface: type[T], implementation: Any) -> T: ...


# Rename to include Protocol suffix for consistency
ServiceFactoryProtocol = Callable[[ContainerProtocol], T]
AsyncServiceFactoryProtocol = Callable[[ContainerProtocol], Awaitable[T]]
Lifetime = Literal["singleton", "scoped", "transient"]


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


@runtime_checkable
class ConfigProviderProtocol(Protocol[T_co]):
    """Protocol for config providers used in dependency injection."""

    def get_settings(self) -> T_co:
        """Get the wrapped settings object."""
        ...

    def get_secure_value(self, field_name: str) -> Any:
        """Get the value of a secure field."""
        ...
