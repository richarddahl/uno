# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Registry implementation for event handlers.

This module provides a registry for managing event handlers with
an async-first approach and without DI container dependencies.
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, get_type_hints

from uno.domain.protocols import DomainEventProtocol
from uno.events.errors import EventHandlerError
from uno.events.protocols import (
    EventHandlerProtocol,
    EventRegistryProtocol,
    EventProtocol,
)
from uno.logging.protocols import LoggerProtocol

# Type alias for handler functions that can be either sync or async
type EventHandlerFunction = Callable[[DomainEventProtocol, dict[str, Any] | None], Any]

# Type alias for async event callbacks
type EventCallback = Callable[
    [DomainEventProtocol, dict[str, Any] | None], Awaitable[None]
]

# Type variable for decorator function type
T = TypeVar("T", bound=Callable[..., Any])

# Type alias for handler registration
type HandlerType = EventHandlerProtocol | EventHandlerFunction


class AsyncEventHandlerAdapter:
    """
    Adapter for converting callables into async event handlers.

    This adapter automatically detects whether the provided function is synchronous
    or asynchronous and wraps it appropriately to ensure all handlers present a
    consistent async interface to the event system.

    Implements EventHandlerProtocol through structural typing.
    """

    def __init__(
        self, handler_func: EventHandlerFunction, logger: LoggerProtocol
    ) -> None:
        """Initialize the adapter.

        Args:
            handler_func: The function to adapt (can be sync or async)
            logger: Logger for structured logging
        """
        self.handler_func = handler_func
        self.logger = logger
        self.is_async = inspect.iscoroutinefunction(handler_func)

        # Store the handler name for logging
        self.handler_name = getattr(
            handler_func,
            "__qualname__",
            getattr(handler_func, "__name__", str(handler_func)),
        )

    async def handle(
        self, event: DomainEventProtocol, metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Handle the event by calling the wrapped function.

        Args:
            event: The domain event to handle
            metadata: Optional metadata for the event

        Raises:
            EventHandlerError: If the handler fails
        """
        try:
            if self.is_async:
                if metadata is not None:
                    await self.handler_func(event, metadata)  # type: ignore
                else:
                    await self.handler_func(event)  # type: ignore
            else:
                # Run sync function in a thread pool
                loop = asyncio.get_running_loop()
                if metadata is not None:
                    await loop.run_in_executor(None, self.handler_func, event, metadata)
                else:
                    await loop.run_in_executor(None, self.handler_func, event)
        except Exception as e:
            await self.logger.error(
                "Error in event handler",
                handler=self.handler_name,
                event_type=type(event).__name__,
                error=str(e),
                exc_info=True,
            )
            raise EventHandlerError(
                f"Error in event handler {self.handler_name}: {e}"
            ) from e


class EventHandlerRegistry:
    """Registry for event handlers that maps event types to their handlers."""

    def __init__(self) -> None:
        self._handlers: dict[type[EventProtocol], list[EventHandlerProtocol]] = {}

    def register(self, handler: EventHandlerProtocol) -> None:
        """Register a handler for a specific event type.

        The event type is determined by inspecting the handler's handle method signature.
        """
        # Get the event type from the handler's signature
        hints = get_type_hints(handler.handle)
        if "event" not in hints:
            raise ValueError(
                f"Handler {handler.__class__.__name__} must have an 'event' parameter"
            )

        event_type = hints["event"]

        # Register the handler for this event type
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        self._handlers[event_type].append(handler)

    def get_handlers_for(
        self, event_type: type[EventProtocol]
    ) -> list[EventHandlerProtocol]:
        """Get all handlers registered for a specific event type."""
        return self._handlers.get(event_type, [])

    def clear(self) -> None:
        """Clear all registered handlers."""
        self._handlers.clear()


async def register_event_handler(
    event_type: str,
    handler: HandlerType,
    registry: EventRegistryProtocol,
) -> None:
    """Register an event handler with the registry.

    Args:
        event_type: The event type to handle
        handler: The handler to register (can be a callable or EventHandlerProtocol)
        registry: The registry to register the handler with
    """
    await registry.register(event_type, handler)
