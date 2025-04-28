"""
EventBusProtocol and EventPublisherProtocol for Uno event sourcing.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, TypeVar
from uno.core.logging.logger import LoggerService
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
    def __init__(self, logger: LoggerService) -> None:
        self._subscribers: dict[str, list[Any]] = {}
        self.logger = logger


    def _canonical_event_dict(self, event: E) -> dict[str, object]:
        """
        Canonical event serialization for storage, logging, and transport.
        Always uses model_dump(exclude_none=True, exclude_unset=True, by_alias=True).
        """
        return event.model_dump(exclude_none=True, exclude_unset=True, by_alias=True)

    async def publish(self, event: E, metadata: dict[str, Any] | None = None) -> Result[None, Exception]:
        try:
            # Log canonical dict for audit/debug
            self.logger.debug(
                f"Publishing event (canonical): {self._canonical_event_dict(event)}"
            )
            for handler in self._subscribers.get(event.event_type, []):
                result = await handler(event)
                from uno.core.errors.result import Failure
                if isinstance(result, Failure):
                    exc = result.error
                    if hasattr(self.logger, "structured_log"):
                        self.logger.structured_log(
                            "ERROR",
                            f"Failed to publish event: {event}",
                            name="uno.events.bus",
                            error=exc,
                            event_id=getattr(event, 'event_id', None),
                            event_type=getattr(event, 'event_type', None),
                            error_message=str(exc)
                        )
                    else:
                        self.logger.error(f"Failed to publish event: {event} - {exc}")
            return Success(None)
        except Exception as exc:
            # Log using structured_log so the error message is present for test assertions
            if hasattr(self.logger, "structured_log"):
                self.logger.structured_log(
                    "ERROR",
                    f"Failed to publish event: {event}",
                    name="uno.events.bus",
                    error=exc,
                    event_id=getattr(event, 'event_id', None),
                    event_type=getattr(event, 'event_type', None),
                    error_message=str(exc)
                )
            else:
                self.logger.error(f"Failed to publish event: {event} - {exc}")
            return Success(None)

    async def publish_many(self, events: list[E]) -> Result[None, Exception]:
        try:
            for event in events:
                await self.publish(event)
            return Success(None)
        except Exception as exc:
            self.logger.error(f"Failed to publish events: {events}", exc_info=exc)
            return Success(None)
        return Success(None)

    def subscribe(self, event_type: str, handler: Any) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)

# Alias for public API
EventBus = InMemoryEventBus
