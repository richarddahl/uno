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
from typing import Any, TypeVar, cast, overload

from uno.domain.protocols import DomainEventProtocol
from uno.events.errors import EventHandlerError
from uno.events.protocols import EventHandlerProtocol, EventRegistryProtocol
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


class EventHandlerRegistry(EventRegistryProtocol):
    """Registry for event handlers.

    Tracks registered handlers for each event type using an async-first approach
    without DI container dependencies.
    """

    def __init__(self, logger: LoggerProtocol) -> None:
        """Initialize the registry.

        Args:
            logger: Logger for structured logging
        """
        self.logger = logger
        self._handlers: dict[str, list[EventHandlerProtocol]] = {}

    @overload
    async def register(
        self,
        event_type: str,
        handler: EventHandlerProtocol,
    ) -> None: ...

    @overload
    async def register(
        self,
        event_type: str,
        handler: EventHandlerFunction,
    ) -> None: ...

    async def register(
        self,
        event_type: str,
        handler: HandlerType | None = None,
    ) -> None:
        """Register a handler for an event type.

        Args:
            event_type: The event type to handle
            handler: The handler to register (can be any callable or handler implementation)
        """
        if handler is None:
            raise ValueError("Handler cannot be None")

        handler_instance: EventHandlerProtocol
        if isinstance(handler, EventHandlerProtocol):
            handler_instance = handler
        elif callable(handler):
            # Create an adapter for raw functions
            handler_instance = AsyncEventHandlerAdapter(
                cast(EventHandlerFunction, handler), self.logger
            )
        else:
            raise TypeError(
                "Handler must be either an EventHandlerProtocol or a callable"
            )

        if event_type not in self._handlers:
            self._handlers[event_type] = []

        self._handlers[event_type].append(handler_instance)

        handler_name = (
            handler_instance.__class__.__name__
            if hasattr(handler_instance, "__class__")
            else str(handler_instance)
        )

        await self.logger.debug(
            "Registered handler for event type",
            event_type=event_type,
            handler_name=handler_name,
        )

    async def get_handlers_for_event(
        self, event: DomainEventProtocol
    ) -> list[EventHandlerProtocol]:
        """Get all handlers for an event.

        Args:
            event: The domain event to get handlers for

        Returns:
            List of handlers for the event
        """
        event_type = getattr(event, "event_type", None)
        if event_type is None:
            await self.logger.warning(
                "Event has no event_type attribute", event=str(event)
            )
            return []
        return self._handlers.get(event_type, [])

    async def clear(self) -> None:
        """Clear all handlers in the registry."""
        self._handlers.clear()
        await self.logger.debug("Cleared all handlers")


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
