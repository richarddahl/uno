"""
Protocol definitions for the uno DI system.

This module contains the core protocols that define the interface for the DI container and its components.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Any, Literal, Protocol, TypeVar, runtime_checkable
from uno.types import T
from uno.di.types import T_co


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

    async def __getitem__(self, key: type[T]) -> T:
        """Get a service by type asynchronously."""
        ...

    async def __setitem__(self, key: type[T], value: T) -> None:
        """Set a service by type asynchronously."""
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


# ServiceFactoryProtocol definitions
ServiceFactoryProtocol = Callable[["ContainerProtocol"], T]
AsyncServiceFactoryProtocol = Callable[["ContainerProtocol"], Awaitable[T]]
Lifetime = Literal["singleton", "scoped", "transient"]


@runtime_checkable
class ContainerProtocol(Protocol):
    async def dispose_services(self, services: list[Any]) -> None:
        """Dispose of a list of services."""
        ...
    """Protocol for dependency injection containers."""

    async def register_singleton(
        self,
        interface: type[T],
        implementation: (
            type[T] | ServiceFactoryProtocol[T] | AsyncServiceFactoryProtocol[T]
        ),
        replace: bool = False,
    ) -> None:
        """Register a service with singleton lifetime."""
        ...

    async def register_scoped(
        self,
        interface: type[T],
        implementation: (
            type[T] | ServiceFactoryProtocol[T] | AsyncServiceFactoryProtocol[T]
        ),
        replace: bool = False,
    ) -> None:
        """Register a service with scoped lifetime."""
        ...

    async def register_transient(
        self,
        interface: type[T],
        implementation: (
            type[T] | ServiceFactoryProtocol[T] | AsyncServiceFactoryProtocol[T]
        ),
        replace: bool = False,
    ) -> None:
        """Register a service with transient lifetime."""
        ...

    async def get_registration_keys(self) -> list[str]:
        """Get all registered service keys asynchronously."""
        ...

    async def get_scope_chain(self) -> list[ScopeProtocol]:
        """Get the chain of scopes from current to root asynchronously."""
        ...

    @contextlib.asynccontextmanager  # type: ignore
    async def create_scope(self) -> AsyncGenerator[ScopeProtocol, None]:
        """Create a new scope for scoped services."""
        ...

    async def wait_for_pending_tasks(self) -> None:
        """Wait for all pending registration tasks to complete."""
        ...

    async def dispose(self) -> None:
        """Dispose the container and all its services."""
        ...

    async def resolve(self, interface: type[T]) -> T:
        """Resolve a service by type."""
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
