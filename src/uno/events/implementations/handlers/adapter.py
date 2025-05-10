# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Adapter implementations for event handlers.

This module provides adapters for wrapping various types of callables as
event handlers, ensuring they all present a consistent async interface.
"""

import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from uno.events.errors import EventHandlerError

if TYPE_CHECKING:
    from uno.events.base_event import DomainEvent
    from uno.logging.protocols import LoggerProtocol


class AsyncEventHandlerAdapter:
    """
    Adapter for converting sync/async callables into async event handlers.

    This adapter automatically detects whether the provided function is synchronous
    or asynchronous and wraps it appropriately to ensure all handlers present a
    consistent async interface to the event system.
    """

    def __init__(
        self,
        handler_func: Callable[
            [
                "DomainEvent",
            ],
            Any,
        ],
        logger: "LoggerProtocol",
    ):
        """
        Initialize the adapter.

        Args:
            handler_func: The function to adapt (can be sync or async)
            logger: Logger for structured logging
        """
        self.handler_func = handler_func
        self.logger = logger
        self.is_async = inspect.iscoroutinefunction(handler_func)

        # Store the handler name for logging
        if hasattr(handler_func, "__qualname__"):
            self.handler_name = handler_func.__qualname__
        elif hasattr(handler_func, "__name__"):
            self.handler_name = handler_func.__name__
        else:
            self.handler_name = str(handler_func)

    async def handle(self, event: "DomainEvent") -> None:
        """
        Handle the event.

        Args:
            event: The domain event to handle

        Raises:
            EventHandlerError: If the handler encounters an error
        """
        try:
            if self.is_async:
                await self.handler_func(event)
            else:
                self.handler_func(event)

            self.logger.debug(
                "Handler executed successfully",
                handler=self.handler_name,
                event_type=getattr(event, "event_type", None),
                event_id=getattr(event, "event_id", None),
            )
        except Exception as e:
            self.logger.error(
                "Handler execution failed",
                handler=self.handler_name,
                event_type=getattr(event, "event_type", None),
                event_id=getattr(event, "event_id", None),
                error=str(e),
                exc_info=e,
            )

            if isinstance(e, EventHandlerError):
                raise

            raise EventHandlerError(
                event_type=getattr(event, "event_type", type(event).__name__),
                handler_name=self.handler_name,
                reason=str(e),
            ) from e
