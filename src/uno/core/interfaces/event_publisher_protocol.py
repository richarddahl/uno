"""
EventPublisherProtocol: Protocol for event publishers (decoupled publishing interface).
"""

from typing import Protocol, Any


class EventPublisherProtocol(Protocol):
    async def publish(self, event: Any) -> None: ...
    async def publish_many(self, events: list[Any]) -> None: ...
