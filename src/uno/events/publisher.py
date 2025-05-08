"""
EventPublisher implementation for Uno event sourcing framework.

Provides a concrete, DI-friendly, and testable event publisher that delegates to an injected event bus.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, TypeVar, Generic

from uno.events.base_event import DomainEvent
from uno.events.interfaces import EventBusProtocol, EventPublisherProtocol
from uno.errors.result import Failure, Result

if TYPE_CHECKING:
    from uno.infrastructure.logging.logger import LoggerService

E = TypeVar("E", bound=DomainEvent)


class EventPublisher(EventPublisherProtocol, Generic[E]):
    """
    Concrete event publisher that delegates to an injected event bus.
    Implements EventPublisherProtocol.

    Canonical Serialization Contract:
        - All events published/logged MUST use `model_dump(exclude_none=True, exclude_unset=True, by_alias=True)` for serialization, storage, and transport.
        - This contract is enforced by logging the canonical dict form of each event.

    Error Handling:
        - All public methods return a Result type for error propagation.
        - Errors are logged using structured logging when possible.
    """

    def __init__(
        self,
        event_bus: EventBusProtocol,
        logger: LoggerService | None = None,
    ) -> None:
        """
        Initialize the event publisher.

        Args:
            event_bus (EventBusProtocol): The event bus to delegate publishing to.
            logger (LoggerService | None): Logger for structured/debug logging. Defaults to a new LoggerService if not provided.
        """
        self.event_bus = event_bus
        from uno.infrastructure.logging.logger import LoggerService, Dev

        self.logger = logger or LoggerService(Dev())
        self.logger = logger or LoggerService(Dev())

    def _canonical_event_dict(self, event: E) -> dict[str, object]:
        """
        Canonical event serialization for storage, logging, and transport.
        Always uses to_dict() for serialization.

        Args:
            event (E): The event to serialize.
        Returns:
            dict[str, object]: Canonical dict suitable for logging/storage.
        """
        return event.to_dict()

    async def publish(self, event: E) -> Result[None, Exception]:
        """
        Publish a single event via the injected event bus.

        Args:
            event (E): The event to publish.
        Returns:
            Result[None, Exception]: Success if published, Failure if any error occurs.
        """
        try:
            self.logger.structured_log(
                "DEBUG",
                "Publishing event (canonical)",
                event=self._canonical_event_dict(event),
            )
            result = await self.event_bus.publish(event)
            if result.is_success:
                self.logger.debug(f"Published event: {event}")
            else:
                self.logger.error(f"Failed to publish event: {event}, result: {result}")
            return result
        except Exception as e:
            self.logger.error(f"Exception during publish: {e!s}")
            return Failure(e)

    async def publish_many(self, events: list[E]) -> Result[None, Exception]:
        """
        Publish a list of events via the injected event bus.

        Args:
            events (list[E]): The events to publish.
        Returns:
            Result[None, Exception]: Success if all published, Failure if any error occurs.
        """
        try:
            for event in events:
                self.logger.structured_log(
                    "DEBUG",
                    "Publishing event (canonical)",
                    event=self._canonical_event_dict(event),
                )
            result = await self.event_bus.publish_many(events)
            if result.is_success:
                self.logger.debug(f"Published {len(events)} events")
            else:
                self.logger.error(f"Failed to publish events, result: {result}")
            return result
        except Exception as e:
            self.logger.error(f"Exception during publish_many: {e!s}")
            return Failure(e)
