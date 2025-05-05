"""
ServiceProtocol: Protocol for service classes.
"""

from typing import Protocol, TypeVar, Generic, Any

T = TypeVar("T")


class ServiceProtocol(Protocol, Generic[T]):
    async def execute(self, *args, **kwargs) -> T: ...
