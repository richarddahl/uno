"""
Service registration implementation for uno DI system.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, Literal

from uno.di.types import T
from uno.di.protocols import ContainerProtocol
from uno.logging.scope import LoggerScope, LoggerScopeProtocol
from uno.logging.factory import LoggerFactory, LoggerFactoryProtocol

if TYPE_CHECKING:
    from uno.di.types import (
        AsyncServiceFactoryProtocol,
        ServiceFactoryProtocol,
    )

def register_logging_services(container: ContainerProtocol) -> None:
    container.register(
        interface=LoggerScopeProtocol,
        implementation=LoggerScope,
        lifetime="scoped",
    )
    container.register(
        interface=LoggerFactoryProtocol,
        implementation=LoggerFactory,
        lifetime="singleton",
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
