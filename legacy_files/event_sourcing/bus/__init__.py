# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework

"""
In-Memory Event Bus Implementation

This module provides an in-memory implementation of the EventBusProtocol,
which can be used for development, testing, or simple applications.
"""

from __future__ import annotations

import asyncio
import sys
from types import TracebackType
from typing import Any, Dict, List, Optional, Tuple, Type, cast

from uno.logging.protocols import LoggerProtocol
from uno.event_sourcing.core.protocols import DomainEventProtocol, EventBusProtocol

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

EventQueueItem: TypeAlias = Tuple[
    Optional[DomainEventProtocol], Optional[Dict[str, Any]]
]


class InMemoryEventBus(EventBusProtocol):
    """
    In-memory implementation of the EventBusProtocol.

    This implementation uses asyncio.Queue for asynchronous event processing
    and supports middleware for cross-cutting concerns.
    """

    def __init__(
        self,
        logger: LoggerProtocol,
        middleware: Optional[List[Any]] = None,
    ) -> None:
        """
        Initialize the in-memory event bus.

        Args:
            logger: Logger for structured logging
            middleware: Optional list of middleware to apply to events
        """
        self.logger = logger
        self.middleware = middleware or []
        self._handlers: Dict[type, List[Any]] = {}
        self._queue: asyncio.Queue[EventQueueItem] = asyncio.Queue()
        self._running: bool = False
        self._task: Optional[asyncio.Task[None]] = None

    async def start(self) -> None:
        """Start the event bus processing loop."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._process_events())
        await self.logger.info("In-memory event bus started")

    async def stop(self) -> None:
        """Stop the event bus processing loop."""
        if not self._running or not self._task:
            return

        self._running = False
        # Add a None sentinel to the queue to stop the processing loop
        await self._queue.put((cast(DomainEventProtocol, None), None))
        await self._task
        self._task = None
        await self.logger.info("In-memory event bus stopped")

    async def publish(
        self, event: DomainEventProtocol, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Publish an event to be processed asynchronously.

        Args:
            event: The domain event to publish
            metadata: Optional metadata to associate with the event

        Raises:
            RuntimeError: If the event bus is not running
        """
        if not self._running:
            raise RuntimeError("Event bus is not running. Call start() first.")

        await self._queue.put((event, metadata))
        await self.logger.debug(
            "Event queued for processing",
            event_type=type(event).__name__,
            event_id=getattr(event, "event_id", None),
        )

    async def publish_many(
        self,
        events: List[DomainEventProtocol],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Publish multiple events to be processed asynchronously.

        Args:
            events: List of domain events to publish
            metadata: Optional metadata to associate with the events
        """
        for event in events:
            await self.publish(event, metadata)

    async def _process_events(self) -> None:
        """Process events from the queue."""
        while self._running:
            event: Optional[DomainEventProtocol] = None
            queue_item: Optional[EventQueueItem] = None
            try:
                queue_item = await self._queue.get()
                if queue_item is None:
                    self._queue.task_done()
                    continue

                event, metadata = queue_item

                # Process the event (None is a shutdown sentinel)
                if event is None:
                    break  # Exit the loop on None sentinel

                # Process the event with its metadata
                event_metadata = metadata or {}
                await self._process_event(event, event_metadata)

            except asyncio.CancelledError:
                await self.logger.info("Event processing cancelled")
                break
            except Exception as e:
                await self.logger.error(
                    "Error processing event",
                    error=str(e),
                    event_type=type(event).__name__ if event is not None else "None",
                    event_id=(
                        getattr(event, "event_id", None) if event is not None else None
                    ),
                    exc_info=True,
                )
            finally:
                if queue_item is not None and queue_item[0] is not None:
                    self._queue.task_done()

    async def _process_event(
        self, event: DomainEventProtocol, metadata: Dict[str, Any]
    ) -> None:
        """Process a single event through the middleware chain."""
        event_type = type(event)

        # Log the event
        await self.logger.debug(
            "Processing event",
            event_type=event_type.__name__,
            event_id=getattr(event, "event_id", None),
        )

        # Get handlers for this event type
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            await self.logger.debug(
                "No handlers registered for event type",
                event_type=event_type.__name__,
            )
            return

        # Process with middleware chain
        await self._apply_middleware(event, metadata, handlers)

    async def _apply_middleware(
        self,
        event: DomainEventProtocol,
        metadata: Dict[str, Any],
        handlers: List[Any],
    ) -> None:
        """Apply middleware chain to the event processing."""

        # Create a handler that will process the event with all handlers
        async def process_with_handlers(
            e: DomainEventProtocol, m: Dict[str, Any]
        ) -> None:
            for handler in handlers:
                try:
                    if hasattr(handler, "handle") and callable(handler.handle):
                        await handler.handle(e, m)
                    elif callable(handler):
                        await handler(e, m)
                except Exception as ex:
                    await self.logger.error(
                        "Error in event handler",
                        error=str(ex),
                        handler=type(handler).__name__,
                        exc_info=True,
                    )

        # Build the middleware chain
        chain = process_with_handlers
        for mw in reversed(self.middleware):
            if hasattr(mw, "process") and callable(mw.process):
                chain = (
                    lambda next_chain, mw: lambda e, m: mw.process(e, next_chain, m)
                )(chain, mw)

        # Execute the middleware chain
        await chain(event, metadata)

    async def register_handler(
        self, event_type: type[DomainEventProtocol], handler: Any
    ) -> None:
        """
        Register a handler for a specific event type.

        Args:
            event_type: The event type to handle
            handler: The handler to register (must have a handle method or be callable)
        """
        if not hasattr(handler, "handle") and not callable(handler):
            raise ValueError("Handler must have a 'handle' method or be callable")

        if event_type not in self._handlers:
            self._handlers[event_type] = []

        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
            await self.logger.debug(
                "Registered handler for event type",
                event_type=event_type.__name__,
                handler=handler.__class__.__name__,
            )

    async def unregister_handler(
        self, event_type: type[DomainEventProtocol], handler: Any
    ) -> None:
        """
        Unregister a handler for a specific event type.

        Args:
            event_type: The event type to unregister from
            handler: The handler to unregister
        """
        if event_type in self._handlers:
            if handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)
                await self.logger.debug(
                    "Unregistered handler for event type",
                    event_type=event_type.__name__,
                    handler=handler.__class__.__name__,
                )

    async def clear_handlers(self) -> None:
        """Clear all registered handlers."""
        self._handlers.clear()
        await self.logger.info("Cleared all event handlers")

    async def __aenter__(self) -> "InMemoryEventBus":
        """Context manager entry."""
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """
        Context manager exit.

        Args:
            exc_type: The exception type if an exception was raised, None otherwise
            exc_val: The exception instance if an exception was raised, None otherwise
            exc_tb: The traceback if an exception was raised, None otherwise
        """
        await self.stop()


# Export the main class
__all__ = ["InMemoryEventBus"]
