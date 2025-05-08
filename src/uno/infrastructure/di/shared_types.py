"""
Shared type definitions to avoid circular dependencies.
"""

from typing import Any, Literal, Protocol, TypeVar

T = TypeVar("T", bound=Any)
T_co = TypeVar("T_co", covariant=True)


class ContainerProtocol(Protocol):
    """Protocol for DI container."""

    _registrations: dict[type[Any], Any]
    _singleton_scope: Any

    async def resolve(self, service_type: type[T]) -> T: ...

    async def _dispose_service(self, service: T) -> None: ...

    async def _create_service(self, interface: type[T], implementation: Any) -> T: ...
