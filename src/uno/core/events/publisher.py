"""
EventPublisher implementation for Uno event sourcing framework.

Provides a concrete, DI-friendly, and testable event publisher that delegates to an injected event bus.
"""
from __future__ import annotations
from typing import TypeVar, Generic

from uno.core.events.base_event import DomainEvent
from uno.core.events.interfaces import EventPublisherProtocol, EventBusProtocol
from uno.core.errors.result import Result, Success, Failure
from uno.core.logging.logger import LoggerService

E = TypeVar("E", bound=DomainEvent)

class EventPublisher(EventPublisherProtocol, Generic[E]):
    """
    Concrete event publisher that delegates to an injected event bus.
    Implements EventPublisherProtocol.

    Canonical serialization contract:
      - All events published/logged MUST use `model_dump(exclude_none=True, exclude_unset=True, by_alias=True)` for serialization, storage, and transport.
      - This contract is enforced by logging the canonical dict form of each event.
    """
    def __init__(
        self,
        event_bus: EventBusProtocol,
        logger: LoggerService | None = None,
    ) -> None:
        self.event_bus = event_bus
        # from uno.core.logging.config import LoggingConfig  # Disabled: no such module, not needed for tests
        self.logger = logger or LoggerService()  # Removed LoggingConfig()

    def _canonical_event_dict(self, event: E) -> dict[str, object]:
        """
        Canonical event serialization for storage, logging, and transport.
        Always uses to_canonical_dict() for serialization.
        """
        return event.to_canonical_dict()

    async def publish(self, event: E) -> Result[None, Exception]:
        try:
            # Log canonical dict for audit/debug
            self.logger.structured_log(
                "DEBUG",
                "Publishing event (canonical)",
                event=self._canonical_event_dict(event)
            )
            result = await self.event_bus.publish(event)
            if result.is_success:
                self.logger.debug(f"Published event: {event}")
            else:
                self.logger.error(f"Failed to publish event: {event}, error: {result.error}")
            return result
        except Exception as e:
            self.logger.error(f"Exception during publish: {e!s}")
            return Failure(e)

    async def publish_many(self, events: list[E]) -> Result[None, Exception]:
        try:
            for event in events:
                self.logger.structured_log(
                    "DEBUG",
                    "Publishing event (canonical)",
                    event=self._canonical_event_dict(event)
                )
            result = await self.event_bus.publish_many(events)
            if result.is_success:
                self.logger.debug(f"Published {len(events)} events")
            else:
                self.logger.error(f"Failed to publish events, error: {result.error}")
            return result
        except Exception as e:
            self.logger.error(f"Exception during publish_many: {e!s}")
            return Failure(e)
