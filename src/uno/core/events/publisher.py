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
    """
    def __init__(
        self,
        event_bus: EventBusProtocol,
        logger: LoggerService | None = None,
    ) -> None:
        self.event_bus = event_bus
        from uno.core.logging.config import LoggingConfig
        self.logger = logger or LoggerService(LoggingConfig())

    async def publish(self, event: E) -> Result[None, Exception]:
        try:
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
            result = await self.event_bus.publish_many(events)
            if result.is_success:
                self.logger.debug(f"Published {len(events)} events")
            else:
                self.logger.error(f"Failed to publish events, error: {result.error}")
            return result
        except Exception as e:
            self.logger.error(f"Exception during publish_many: {e!s}")
            return Failure(e)
