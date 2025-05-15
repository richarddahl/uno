"""
EventPublisher implementation for Uno event sourcing framework.

Provides a concrete, DI-friendly, and testable event publisher that delegates to an injected event bus.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, TypeVar, Generic, cast, Any

from uno.events.protocols import DomainEventProtocol, EventBusProtocol
from uno.events.errors import EventPublishError
from pydantic import BaseModel


if TYPE_CHECKING:
    from uno.logging.protocols import LoggerProtocol

E = TypeVar("E", bound=DomainEventProtocol)


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
        logger: LoggerProtocol,
    ) -> None:
        """Initialize the event publisher.

        Args:
            event_bus: The event bus to delegate publishing to.
            logger: Logger for structured/debug logging.

        Note:
            Type checking is handled by the type system at compile time.
            No runtime type checking is performed for performance reasons.
        """
        self.event_bus = event_bus
        self.logger = logger

    def _canonical_event_dict(self, event: E) -> dict[str, Any]:
        """
        Canonical event serialization for storage, logging, and transport.
        
        Args:
            event: The event to serialize.
            
        Returns:
            Dictionary containing the event's data.
            
        Note:
            Uses Pydantic's model_dump() for serialization.
        """
        if not isinstance(event, BaseModel):
            raise TypeError(f"Event {event} is not a Pydantic model")
        return event.model_dump(exclude_none=True, exclude_unset=True, by_alias=True)

    async def publish(self, event: E) -> None:
        """
        Publish a single event via the injected event bus.
        Raises:
            EventPublishError: if publishing fails
        """
        try:
            event_dict = self._canonical_event_dict(event)
            if self.logger:
                await self.logger.debug(
                    f"Publishing event (canonical): {event_dict}"
                )
            # Cast to DomainEventProtocol to satisfy type checker
            await self.event_bus.publish(cast(DomainEventProtocol, event))
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
        
        Args:
            events: List of events to publish
            
        Raises:
            EventPublishError: If publishing any event fails
            
        Note:
            Events are published in the order they appear in the list.
            If an error occurs, no further events will be published.
        """
        try:
            if self.logger:
                for event in events:
                    event_dict = self._canonical_event_dict(event)
                    await self.logger.debug(
                        f"Publishing event (canonical): {event_dict}"
                    )
            # Cast to list[DomainEventProtocol] to satisfy type checker
            await self.event_bus.publish_many(cast(list[DomainEventProtocol], events))
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
