# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Registry implementation for event handlers.

This module provides a registry for managing event handlers and handler
discovery functionality.
"""

from typing import Any, TYPE_CHECKING

from uno.events.implementations.handlers.adapter import AsyncEventHandlerAdapter

if TYPE_CHECKING:
    from uno.logging.protocols import LoggerProtocol


class EventHandlerRegistry:
    """
    Registry for event handlers.

    Tracks registered handlers for each event type and maintains their
    dependencies and configuration.
    """

    def __init__(self, logger: "LoggerProtocol") -> None:
        """
        Initialize the registry.

        Args:
            logger: Logger for structured logging
        """
        self.logger = logger
        self._handlers: dict[str, list[Any]] = {}

    def register_handler(self, event_type: str, handler: Any) -> None:
        """
        Register a handler for an event type.

        Args:
            event_type: The event type to handle
            handler: The handler to register (can be any callable or handler implementation)
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        # Create an async adapter if the handler doesn't seem to be a handler
        # with an async handle method already
        if not hasattr(handler, "handle") or not callable(handler.handle):
            # Create an adapter that handles both sync and async callables
            handler_adapter = AsyncEventHandlerAdapter(handler, self.logger)
            self._handlers[event_type].append(handler_adapter)

            self.logger.debug(
                "Registered callable handler for event type",
                event_type=event_type,
                handler_type="AsyncEventHandlerAdapter",
            )
        else:
            # Handler is already a handler instance
            self._handlers[event_type].append(handler)

            handler_name = handler.__class__.__name__
            self.logger.debug(
                "Registered handler for event type",
                event_type=event_type,
                handler_name=handler_name,
            )

    def get_handlers(self, event_type: str) -> list[Any]:
        """
        Get all handlers for an event type.

        Args:
            event_type: The event type to get handlers for

        Returns:
            List of handlers for the event type
        """
        return self._handlers.get(event_type, [])

    def clear(self) -> None:
        """Clear all handlers in the registry."""
        self._handlers.clear()
        self.logger.debug("Cleared all handlers")
