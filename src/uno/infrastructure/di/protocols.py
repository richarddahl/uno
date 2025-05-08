"""
Protocol definitions for the uno DI system.

This module contains the core protocols that define the interface for the DI container and its components.
"""

from collections.abc import Callable
from typing import Any, Protocol, TypeVar, runtime_checkable

__all__ = [
    "ContainerProtocol",
    "ScopeProtocol",
    "ServiceProtocol",
    "ServiceRegistrationProtocol",
]

T = TypeVar("T")


@runtime_checkable
class ContainerProtocol(Protocol):
    """Protocol for the DI container."""

    async def register_singleton(
        self, interface: type[T], implementation: type[T] | Callable[..., T]
    ) -> None:
        """Register a singleton service."""
        ...

    async def register_scoped(
        self, interface: type[T], implementation: type[T] | Callable[..., T]
    ) -> None:
        """Register a scoped service."""
        ...

    async def register_transient(
        self, interface: type[T], implementation: type[T] | Callable[..., T]
    ) -> None:
        """Register a transient service."""
        ...

    async def resolve(self, interface: type[T]) -> T:
        """Resolve a service."""
        ...

    async def create_scope(self) -> "ScopeProtocol":
        """Create a new scope."""
        ...


@runtime_checkable
class ScopeProtocol(Protocol):
    """Protocol for a DI scope."""

    async def resolve(self, interface: type[T]) -> T:
        """Resolve a service within this scope."""
        ...


@runtime_checkable
class ServiceProtocol(Protocol):
    """Protocol for a service."""

    ...


@runtime_checkable
class ServiceRegistrationProtocol(Protocol):
    """Protocol for service registration."""

    interface: type[Any]
    implementation: type[Any] | Callable[..., Any]
    lifetime: str  # "singleton", "scoped", or "transient"

    def __init__(
        self,
        interface: type[Any],
        implementation: type[Any] | Callable[..., Any],
        lifetime: str,
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
