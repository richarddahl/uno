"""
EventBusProtocol and EventPublisherProtocol for Uno event sourcing.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Protocol, TypeVar, Awaitable
from uno.core.events.base_event import DomainEvent
from uno.core.events.interfaces import EventBusProtocol, EventPublisherProtocol
from uno.core.errors.result import Result

E = TypeVar("E", bound=DomainEvent)


class InMemoryEventBus(EventBusProtocol):
    """
    Simple in-memory event bus for development/testing.
    """
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Any]] = {}

    async def publish(self, event: E, metadata: dict[str, Any] | None = None) -> Result[None, Exception]:
        for handler in self._subscribers.get(event.event_type, []):
            await handler(event)
        return Result.success(None)

    async def publish_many(self, events: list[E]) -> Result[None, Exception]:
        for event in events:
            await self.publish(event)
        return Result.success(None)

    def subscribe(self, event_type: str, handler: Any) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)

# Alias for public API
EventBus = InMemoryEventBus
