"""
EventBusProtocol and EventPublisherProtocol for Uno event sourcing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from uno.events.base_event import DomainEvent
from uno.events.errors import (
    EventErrorCode,
    EventHandlerError,
    EventPublishError,
    UnoError as AppError,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from uno.events.config import EventsConfig
    from uno.logging.protocols import LoggerProtocol

E = TypeVar("E", bound=DomainEvent)


class InMemoryEventBus:
    """
    In-memory implementation of event bus.

    Args:
        logger: Logger instance for structured logging
        config: Events configuration settings

    Error Handling:
        - Uses structured exception-based error handling with AppError
        - Errors are logged using structured logging

    Type Parameters:
        - E: DomainEvent (or subclass)
    """

    def __init__(self, logger: LoggerProtocol, config: EventsConfig) -> None:
        """
        Initialize the in-memory event bus.

        Args:
            logger: Logger instance for structured logging
            config: Events configuration settings
        """
        self._subscribers: dict[str, list[Callable[[E], Awaitable[None]]]] = {}
        self.logger = logger
        self.config = config

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

    async def publish(self, event: E, metadata: dict[str, Any] | None = None) -> None:
        """
        Publish a single event to all subscribers.

        Args:
            event: The event to publish
            metadata: Optional metadata for the event

        Raises:
            EventPublishError: If publishing fails
            EventHandlerError: If any handler fails
        """
        metadata = metadata or {}

        try:
            # Log canonical dict for audit/debug
            self.logger.debug(
                "Publishing event",
                event_data=self._canonical_event_dict(event),
                event_type=getattr(event, "event_type", None),
                event_id=getattr(event, "event_id", None),
                metadata=metadata,
            )

            handlers = self._subscribers.get(event.event_type, [])

            if not handlers:
                self.logger.debug(
                    "No handlers registered for event",
                    event_type=event.event_type,
                    event_id=getattr(event, "event_id", None),
                )
                return

            for handler in handlers:
                try:
                    await handler(event)
                except Exception as exc:
                    self.logger.error(
                        "Handler failed for event",
                        event_id=getattr(event, "event_id", None),
                        event_type=getattr(event, "event_type", None),
                        handler=str(handler),
                        error=str(exc),
                        metadata=metadata,
                        exc_info=exc,
                    )

                    # Retry logic based on configuration
                    if self.config.retry_attempts > 0:
                        await self._retry_handler(handler, event, metadata)
                    else:
                        raise AppError(
                            code=EventErrorCode.HANDLER_ERROR,
                            message=f"Handler failed for event {event.event_type}",
                            context={
                                "event_type": event.event_type,
                                "handler_name": str(handler),
                                "error": str(exc),
                            },
                        ) from exc

            self.logger.debug(
                "Event published successfully",
                event_type=event.event_type,
                event_id=getattr(event, "event_id", None),
                handler_count=len(handlers),
            )

        except Exception as exc:
            self.logger.error(
                "Failed to publish event",
                event_id=getattr(event, "event_id", None),
                event_type=getattr(event, "event_type", None),
                error=str(exc),
                metadata=metadata,
                exc_info=exc,
            )

            if isinstance(exc, EventPublishError | EventHandlerError):
                raise

            raise AppError(
                code=EventErrorCode.PUBLISH_ERROR,
                message="Failed to publish event",
                context={
                    "event_type": getattr(event, "event_type", type(event).__name__),
                    "error": str(exc),
                },
            ) from exc

    async def _retry_handler(
        self, handler: Any, event: E, metadata: dict[str, Any]
    ) -> None:
        """
        Retry a failed handler based on configuration settings.

        Args:
            handler: The event handler to retry
            event: The event to handle
            metadata: Event metadata

        Raises:
            EventHandlerError: If all retry attempts fail
        """
        import asyncio

        retry_count = 0
        last_error = None

        while retry_count < self.config.retry_attempts:
            retry_count += 1

            # Wait before retrying
            await asyncio.sleep(self.config.retry_delay_ms / 1000.0)

            try:
                self.logger.info(
                    "Retrying event handler",
                    event_id=getattr(event, "event_id", None),
                    event_type=getattr(event, "event_type", None),
                    handler=str(handler),
                    retry_count=retry_count,
                    max_retries=self.config.retry_attempts,
                )

                await handler(event)

                self.logger.info(
                    "Retry succeeded",
                    event_id=getattr(event, "event_id", None),
                    event_type=getattr(event, "event_type", None),
                    handler=str(handler),
                    retry_count=retry_count,
                )

                return
            except Exception as exc:
                last_error = exc
                self.logger.warning(
                    "Retry failed",
                    event_id=getattr(event, "event_id", None),
                    event_type=getattr(event, "event_type", None),
                    handler=str(handler),
                    retry_count=retry_count,
                    max_retries=self.config.retry_attempts,
                    error=str(exc),
                )

        # All retries failed
        self.logger.error(
            "All retry attempts failed",
            event_id=getattr(event, "event_id", None),
            event_type=getattr(event, "event_type", None),
            handler=str(handler),
            retry_count=retry_count,
            max_retries=self.config.retry_attempts,
        )

        if last_error:
            raise EventHandlerError(
                event_type=event.event_type,
                handler_name=str(handler),
                reason="All retry attempts failed for event handler",
                context={
                    "event_type": getattr(event, "event_type", type(event).__name__),
                    "handler_name": str(handler),
                    "retry_count": retry_count,
                    "error": str(last_error),
                },
            ) from last_error

    async def publish_many(self, events: list[E]) -> None:
        """
        Publish a list of events to all subscribers.

        Args:
            events: The events to publish

        Raises:
            EventPublishError: If publishing any event fails
        """
        if not events:
            self.logger.debug("No events to publish")
            return

        self.logger.info("Publishing multiple events", event_count=len(events))

        for event in events:
            await self.publish(event)

        self.logger.debug("All events published successfully", event_count=len(events))

    def subscribe(self, event_type: str, handler: Any) -> None:
        """
        Subscribe a handler to a specific event type.

        Args:
            event_type: The event type to subscribe to
            handler: The handler function/coroutine to invoke for this event type
        """
        self.logger.debug(
            "Subscribing handler to event type",
            event_type=event_type,
            handler=str(handler),
        )

        self._subscribers.setdefault(event_type, []).append(handler)


# Alias for public API
EventBus = InMemoryEventBus
