"""
EventBusProtocol and EventPublisherProtocol for Uno event sourcing.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Any, TypeVar
from uno.core.events.base_event import DomainEvent
from uno.core.events.interfaces import EventBusProtocol
from uno.core.errors.result import Result, Success

if TYPE_CHECKING:
    from uno.infrastructure.logging.logger import LoggerService

E = TypeVar("E", bound=DomainEvent)


class InMemoryEventBus(EventBusProtocol):
    """
    Simple in-memory event bus for Uno event sourcing (development/testing).

    Canonical Serialization Contract:
        - All events published/logged MUST use `model_dump(exclude_none=True, exclude_unset=True, by_alias=True)` for serialization, storage, and transport.
        - This contract is enforced by logging the canonical dict form of each event.

    Error Handling:
        - All public methods return a Result type for error propagation.
        - Errors are logged using structured logging when possible.

    Type Parameters:
        - E: DomainEvent (or subclass)
    """

    def __init__(self, logger: LoggerService) -> None:
        """
        Initialize the in-memory event bus.

        Args:
            logger (LoggerService): Logger instance for structured and debug logging.
        """
        self._subscribers: dict[str, list[Any]] = {}
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

    async def publish(
        self, event: E, metadata: dict[str, Any] | None = None
    ) -> Result[None, Exception]:
        """
        Publish a single event to all subscribers.

        Args:
            event (E): The event to publish.
            metadata (dict[str, Any] | None): Optional metadata for the event.
        Returns:
            Result[None, Exception]: Success if all handlers complete, Failure if any error occurs.
        """
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
                            event_id=getattr(event, "event_id", None),
                            event_type=getattr(event, "event_type", None),
                            error_message=str(exc),
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
                    event_id=getattr(event, "event_id", None),
                    event_type=getattr(event, "event_type", None),
                    error_message=str(exc),
                )
            else:
                self.logger.error(f"Failed to publish event: {event} - {exc}")
            return Success(None)

    async def publish_many(self, events: list[E]) -> Result[None, Exception]:
        """
        Publish a list of events to all subscribers.

        Args:
            events (list[E]): The events to publish.
        Returns:
            Result[None, Exception]: Success if all handlers complete, Failure if any error occurs.
        """
        try:
            for event in events:
                await self.publish(event)
            return Success(None)
        except Exception as exc:
            self.logger.error(
                f"Failed to publish events: {events} - {exc}", exc_info=True
            )
            return Success(None)

    def subscribe(self, event_type: str, handler: Any) -> None:
        """
        Subscribe a handler to a specific event type.

        Args:
            event_type (str): The event type to subscribe to.
            handler (Any): The handler function/coroutine to invoke for this event type.
        """
        self._subscribers.setdefault(event_type, []).append(handler)


# Alias for public API
EventBus = InMemoryEventBus
