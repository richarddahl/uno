# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
events.bus
In-memory event bus implementation for Uno framework
"""

from __future__ import annotations
from typing import (
    TypeVar,
    Generic,
    Callable,
    Any,
    Awaitable,
    cast,
    Type,
    TypeVar,
    Coroutine,
    Optional,
)
import asyncio
from uno.logging import LoggerProtocol
from uno.event_bus.protocols import (
    EventBusProtocol,
    EventMiddlewareProtocol,
    DomainEventProtocol,
)
from uno.event_bus.errors import EventBusPublishError, EventBusSubscribeError

E = TypeVar("E", bound=DomainEventProtocol)


class EventBus(Generic[E]):
    """Base event bus implementation that implements EventBusProtocol[E].

    This class provides a foundation for implementing an event bus that can publish
    events and process them through middleware and handlers asynchronously.
    """

    def __init__(self, logger: LoggerProtocol) -> None:
        """Initialize the event bus with a logger.

        Args:
            logger: Logger instance for logging events and errors
        """
        self._handlers: dict[str, list[Callable[[E], Awaitable[None]]]] = {}
        self._middleware: list[EventMiddlewareProtocol[E]] = []
        self._logger = logger

    def publish(self, event: E) -> None:
        """Publish a single event asynchronously.

        Args:
            event: The event to publish
        """

        async def _publish() -> None:
            try:
                await self._process_event(event)
            except Exception as e:
                await self._handle_publish_error(event, e)

        # Schedule the coroutine to run in the background
        asyncio.create_task(_publish())

    def publish_many(self, events: list[E]) -> None:
        """Publish multiple events asynchronously.

        Args:
            events: List of events to publish
        """
        for event in events:
            self.publish(event)

    async def _handle_publish_error(self, event: E, error: Exception) -> None:
        """Handle errors during event publishing."""
        # Fire and forget the error logging
        self._logger.error(
            "Error publishing event", event_type=type(event).__name__, error=str(error)
        )
        # Create the error but don't await it
        EventBusPublishError.async_init(
            f"Failed to publish event: {str(error)}",
            code=EventBusPublishError.code,
            severity=EventBusPublishError.severity,
        )

    async def _process_event(self, event: E) -> None:
        """Process an event through middleware and handlers.

        Args:
            event: The event to process
        """
        event_type = type(event).__name__
        handlers = self._handlers.get(event_type, [])

        # Process through middleware
        async def process_middleware(
            middleware: EventMiddlewareProtocol[E], e: E
        ) -> None:
            async def next_handler(evt: E) -> None:
                await self._invoke_handlers(evt, handlers)

            await middleware.process(e, next_handler)

        if self._middleware:
            await process_middleware(self._middleware[0], event)
        else:
            await self._invoke_handlers(event, handlers)

    async def _invoke_handlers(
        self, event: E, handlers: list[Callable[[E], Awaitable[None]]]
    ) -> None:
        """Invoke all handlers for an event.

        Args:
            event: The event to process
            handlers: List of handler functions to invoke
        """
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                await self._handle_handler_error(handler, event, e)

    async def _handle_handler_error(
        self, handler: Callable[..., Any], event: E, error: Exception
    ) -> None:
        """Handle errors in event handlers.

        Args:
            handler: The handler that raised the error
            event: The event being processed
            error: The exception that was raised
        """
        # Log the error
        self._logger.error(
            "Error in event handler",
            handler=str(handler),
            event_type=type(event).__name__,
            error=str(error),
        )

        # Create and raise the error
        error_event = EventBusSubscribeError.async_init(
            f"Handler failed for event: {str(error)}",
            code=EventBusSubscribeError.code,
            severity=EventBusSubscribeError.severity,
            context={
                "handler": str(handler),
                "event_type": type(event).__name__,
                "error": str(error),
            },
        )

        # Raise the error to be handled by the caller
        if error_event is not None and isinstance(error_event, Exception):
            raise error_event from error


class InMemoryEventBus(EventBus[E]):
    """In-memory implementation of EventBus."""

    pass
