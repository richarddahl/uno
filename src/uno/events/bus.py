"""
EventBusProtocol and EventPublisherProtocol for Uno event sourcing.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, TypeVar

from uno.events.base_event import DomainEvent
from uno.events.errors import (
    EventErrorCode,
    EventHandlerError,
)
from uno.events.metrics import EventMetrics

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

    def __init__(
        self,
        logger: LoggerProtocol,
        config: EventsConfig,
        metrics_factory: Any | None = None,
    ) -> None:
        """
        Initialize the in-memory event bus.

        Args:
            logger: Logger instance for structured logging
            config: Events configuration settings
            metrics_factory: Optional metrics factory for collecting event metrics
        """
        self._subscribers: dict[str, list[Callable[[E], Awaitable[None]]]] = {}
        self.logger = logger
        self.config = config
        self.metrics = (
            EventMetrics(metrics_factory, logger) if metrics_factory else None
        )

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
        """Publish an event to all registered handlers.

        Args:
            event: The event to publish
            metadata: Optional metadata to include with the event
        """
        # Record metrics before publishing
        if self.metrics:
            await self.metrics.record_event_published(event)
            await self.metrics.increment_active_events(event)

        # Get the event type name
        event_type = event.__class__.__name__

        # Log the event
        event_id = getattr(event, "event_id", None)
        await self.logger.debug(
            "Publishing event", event_type=event_type, event_id=event_id
        )

        # Get all handlers for this event type and its superclasses
        handlers = self._subscribers.get(event.event_type, [])

        if not handlers:
            await self.logger.debug(
                "No handlers found for event", event_type=event_type
            )
            # Decrement active events since we're not processing any handlers
            if self.metrics:
                await self.metrics.decrement_active_events(event)
            return

        # Execute all handlers concurrently
        tasks = [
            self._execute_handler(handler, event, metadata or {})
            for handler in handlers
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log any exceptions that occurred in handlers
        for result in results:
            if isinstance(result, Exception):
                await self.logger.error(
                    "Error in event handler",
                    error=str(result),
                    error_type=type(result).__name__,
                    exc_info=result,
                )

        # Check for any errors in the results and raise the first one if present
        for result in results:
            if isinstance(result, Exception):
                # Log the error if not already logged
                if not any(
                    isinstance(r, type(result)) for r in results if r is not result
                ):
                    await self.logger.error(
                        "Error in event handler",
                        error=str(result),
                        error_type=type(result).__name__,
                        exc_info=result,
                    )
                raise result

    async def _execute_handler(
        self,
        handler: Callable[[E], Awaitable[None]],
        event: E,
        metadata: dict[str, Any],
    ) -> None:
        """
        Execute a single event handler with error handling and logging.

        Args:
            handler: The handler function to execute
            event: The event to pass to the handler
            metadata: Additional metadata for the event

        Raises:
            EventHandlerError: If the handler fails after all retry attempts
        """
        handler_name = handler.__name__
        event_type = event.__class__.__name__
        event_id = getattr(event, "event_id", None)

        retry_count = 0
        last_error = None

        while retry_count < self.config.retry_attempts:
            try:
                await self.logger.debug(
                    "Executing event handler",
                    handler=handler_name,
                    event_type=event_type,
                    event_id=event_id,
                )

                # Record handler start time for metrics
                start_time = asyncio.get_event_loop().time()

                try:
                    await handler(event)
                    duration = asyncio.get_event_loop().time() - start_time

                    # Record metrics after successful processing
                    if self.metrics:
                        await self.metrics.record_processing_time(event, duration)
                        await self.metrics.record_event_processed(event)

                    # Log successful processing
                    await self.logger.debug(
                        "Successfully processed event",
                        event_type=event_type,
                        event_id=event_id,
                        handler=handler_name,
                        duration_seconds=duration,
                    )
                    return  # Success - exit the retry loop

                except Exception as e:
                    duration = asyncio.get_event_loop().time() - start_time

                    # Record error metrics
                    if self.metrics:
                        await self.metrics.record_event_error(event, e)

                    # Log the error
                    await self.logger.error(
                        "Error processing event",
                        event_type=event_type,
                        event_id=event_id,
                        handler=handler_name,
                        error=str(e),
                        exc_info=True,
                    )
                    last_error = e
                    retry_count += 1

                    if retry_count < self.config.retry_attempts:
                        await self.logger.warning(
                            "Retrying event handler",
                            handler=handler_name,
                            event_type=event_type,
                            event_id=event_id,
                            retry_count=retry_count,
                            max_retries=self.config.retry_attempts,
                        )

            except Exception as e:
                last_error = e
                retry_count += 1
                await self.logger.error(
                    "Unexpected error in event handler execution",
                    handler=handler_name,
                    event_type=event_type,
                    event_id=event_id,
                    error=str(e),
                    exc_info=True,
                )

        # If we get here, all retries failed
        message = (
            f"Handler failed after {self.config.retry_attempts} "
            f"retries for event {event_type}"
        )
        raise EventHandlerError(
            code=EventErrorCode.HANDLER_ERROR,
            message=message,
            event_type=event_type,
            handler_name=handler_name,
            reason=str(last_error) if last_error else "Unknown error",
            context={
                "retry_count": retry_count,
                "last_error": str(last_error) if last_error else None,
            },
        ) from last_error

    async def publish_many(
        self, events: list[E], batch_size: int | None = None
    ) -> None:
        """
        Publish a list of events to all subscribers, in batches and concurrently.

        Args:
            events: The events to publish
            batch_size: Number of events to process concurrently in a batch

        Raises:
            EventPublishError: If publishing any event fails
        """
        if not events:
            await self.logger.debug("No events to publish")
            return

        batch_size = batch_size or getattr(self.config, "batch_size", 10)
        await self.logger.info(
            "Publishing multiple events", event_count=len(events), batch_size=batch_size
        )

        for i in range(0, len(events), batch_size):
            batch = events[i : i + batch_size]
            tasks = [self.publish(event) for event in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    await self.logger.error(
                        "Failed to publish event in batch", error=str(result)
                    )

        await self.logger.debug(
            "All events published successfully", event_count=len(events)
        )

    async def subscribe(self, event_type: str, handler: Any) -> None:
        """
        Subscribe a handler to a specific event type.

        Args:
            event_type: The event type to subscribe to
            handler: The handler function/coroutine to invoke for this event type
        """
        await self.logger.debug(
            "Subscribing handler to event type",
            event_type=event_type,
            handler=(
                handler.__qualname__
                if hasattr(handler, "__qualname__")
                else str(handler)
            ),
        )

        self._subscribers.setdefault(event_type, []).append(handler)


# Alias for public API
EventBus = InMemoryEventBus
