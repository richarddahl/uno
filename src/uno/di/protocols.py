"""
Protocol definitions for the uno DI system.

This module contains the core protocols that define the interface for the DI container and its components.
"""

from collections.abc import Awaitable, Callable
from typing import Any, Literal, Protocol, TypeVar, runtime_checkable

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)


# Need to define ScopeProtocol first so ContainerProtocol can reference it
@runtime_checkable
class ScopeProtocol(Protocol):
    """Protocol for a DI scope."""

    @property
    def id(self) -> str:
        """Get the unique ID of this scope."""
        ...

    @property
    def parent(self) -> "ScopeProtocol | None":
        """Get the parent scope, or None if this is a root scope."""
        ...

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

    def get_service_keys(self) -> list[str]:
        """Get the service keys available in this scope synchronously."""
        ...

    async def get_service_keys(self) -> list[str]:
        """Get the service keys available in this scope asynchronously."""
        ...


@runtime_checkable
class ContainerProtocol(Protocol):
    """Protocol for DI container."""

    _registrations: dict[type[Any], Any]
    _singleton_scope: Any

    @property
    def current_scope(self) -> ScopeProtocol | None:
        """Get the current active scope, or None if no scope is active."""
        ...

    async def resolve(self, service_type: type[T]) -> T: ...

    async def _dispose_service(self, service: T) -> None: ...

    async def _create_service(self, interface: type[T], implementation: Any) -> T: ...

    async def get_registration_keys(self) -> list[str]:
        """Get all registered service keys synchronously."""
        ...

    async def get_registration_keys_async(self) -> list[str]:
        """Get all registered service keys asynchronously."""
        ...

    async def get_scope_chain(self) -> list[ScopeProtocol]:
        """Get the chain of scopes from current to root synchronously."""
        ...

    async def get_scope_chain_async(self) -> list[ScopeProtocol]:
        """Get the chain of scopes from current to root asynchronously."""
        ...


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

    async def create_scope(self) -> "ScopeProtocol":
        """Create a child scope."""
        ...

    async def get_service_keys(self) -> list[str]:
        """Get the service keys available in this scope asynchronously."""
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
