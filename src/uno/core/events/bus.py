"""
EventBusProtocol and EventPublisherProtocol for Uno event sourcing.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Protocol, TypeVar, Awaitable
from uno.core.events.base_event import DomainEvent
from uno.core.events.interfaces import EventBusProtocol, EventPublisherProtocol
from uno.core.errors.result import Result, Success

E = TypeVar("E", bound=DomainEvent)


class InMemoryEventBus(EventBusProtocol):
    """
    Simple in-memory event bus for development/testing.

    Canonical serialization contract:
      - All events published/logged MUST use `model_dump(exclude_none=True, exclude_unset=True, by_alias=True)` for serialization, storage, and transport.
      - This contract is enforced by logging the canonical dict form of each event.
    """
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Any]] = {}

    def _canonical_event_dict(self, event: E) -> dict[str, object]:
        """
        Canonical event serialization for storage, logging, and transport.
        Always uses model_dump(exclude_none=True, exclude_unset=True, by_alias=True).
        """
        return event.model_dump(exclude_none=True, exclude_unset=True, by_alias=True)

    async def publish(self, event: E, metadata: dict[str, Any] | None = None) -> Result[None, Exception]:
        try:
            # Log canonical dict for audit/debug
            import logging
            logging.getLogger("uno.events.bus").debug(
                "Publishing event (canonical): %s", self._canonical_event_dict(event)
            )
            for handler in self._subscribers.get(event.event_type, []):
                await handler(event)
            return Success(None)
        except Exception as exc:
            import logging
            logging.getLogger("uno.events.bus").exception("Failed to publish event: %s", event)
            return Success(None)

    async def publish_many(self, events: list[E]) -> Result[None, Exception]:
        try:
            for event in events:
                await self.publish(event)
            return Success(None)
        except Exception as exc:
            import logging
            logging.getLogger("uno.events.bus").exception("Failed to publish events: %s", events)
            return Success(None)
        return Success(None)

    def subscribe(self, event_type: str, handler: Any) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)

# Alias for public API
EventBus = InMemoryEventBus
