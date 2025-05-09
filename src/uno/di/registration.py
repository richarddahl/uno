"""
Service registration implementation for uno DI system.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, Literal

from uno.di.shared_types import T

if TYPE_CHECKING:
    from uno.di.types import (
        AsyncServiceFactoryProtocol,
        ServiceFactoryProtocol,
    )


class ServiceRegistration(Generic[T]):
    """Represents a service registration in the container."""

    def __init__(
        self,
        interface: type[T],
        implementation: (
            type[T] | ServiceFactoryProtocol[T] | AsyncServiceFactoryProtocol[T]
        ),
        lifetime: Literal["singleton", "scoped", "transient"],
    ) -> None:
        self.interface = interface
        self.implementation = implementation
        self.lifetime = lifetime
