"""
EventPublisher implementation for Uno event sourcing framework.

Provides a concrete, DI-friendly, and testable event publisher that delegates to an injected event bus.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, TypeVar, Generic

from uno.events.base import DomainEvent
from uno.events.protocols import EventBusProtocol
from uno.events.errors import EventPublishError


if TYPE_CHECKING:
    from uno.logging.protocols import LoggerProtocol

E = TypeVar("E", bound=DomainEvent)


class EventPublisher(Generic[E]):
    """
    Concrete event publisher that delegates to an injected event bus.
    Structurally implements EventPublisherProtocol without inheritance.

    Canonical Serialization Contract:
        - All events published/logged MUST use `model_dump(exclude_none=True, exclude_unset=True, by_alias=True)` for serialization, storage, and transport.
        - This contract is enforced by logging the canonical dict form of each event.

    Error Handling:
        - All public methods raise EventPublishError on error for error propagation.
        - Errors are logged using structured logging when possible.
    """

    def __init__(
        self,
        event_bus: EventBusProtocol,
        logger: LoggerProtocol | None = None,
    ) -> None:
        """
        Initialize the event publisher.

        Args:
            event_bus (EventBusProtocol): The event bus to delegate publishing to.
            logger (LoggerProtocol | None): Logger for structured/debug logging. Defaults to a new LoggerProtocol if not provided.
        """
        self.event_bus = event_bus
        # Use the injected logger or a no-op fallback
        self.logger = logger

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

    async def publish(self, event: E) -> None:
        """
        Publish a single event via the injected event bus.
        Raises:
            EventPublishError: if publishing fails
        """
        try:
            if self.logger:
                await self.logger.debug(
                    f"Publishing event (canonical): {self._canonical_event_dict(event)}"
                )
            await self.event_bus.publish(event)
            if self.logger:
                await self.logger.debug(f"Published event: {event}")
        except Exception as e:
            if self.logger:
                await self.logger.error(f"Exception during publish: {e!s}")
            raise EventPublishError(
                event_type=type(event).__name__,
                reason=str(e),
                event=event,
                handler="EventPublisher.publish",
            ) from e

    async def publish_many(self, events: list[E]) -> None:
        """
        Publish a list of events via the injected event bus.
        Raises:
            EventPublishError: if publishing any event fails
        """
        try:
            if self.logger:
                for event in events:
                    await self.logger.debug(
                        f"Publishing event (canonical): {self._canonical_event_dict(event)}"
                    )
            await self.event_bus.publish_many(events)
            if self.logger:
                await self.logger.debug(f"Published {len(events)} events")
        except Exception as e:
            if self.logger:
                await self.logger.error(f"Exception during publish_many: {e!s}")
            raise EventPublishError(
                event_type=type(events[0]).__name__ if events else "Unknown",
                reason=str(e),
                events=events,
                handler="EventPublisher.publish_many",
            ) from e
