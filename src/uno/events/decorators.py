# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Decorators for event handling.

This module provides decorators for registering event handlers.
"""

import asyncio
from typing import Any, Callable, TypeVar

from uno.events.protocols import EventHandlerProtocol, EventRegistryProtocol
from uno.logging.protocols import LoggerProtocol

T = TypeVar("T", bound=Callable[..., Any])


class HandlerDecorator:
    """
    Decorator for event handlers.

    Allows functions and methods to be decorated as event handlers for specific event types.
    """

    _registry: EventRegistryProtocol | None = None

    @classmethod
    def set_registry(cls, registry: EventRegistryProtocol) -> None:
        """Set the registry to use for decorators."""
        cls._registry = registry

    @classmethod
    def handles(cls, event_type: str) -> Callable[[T], T]:
        """Decorator to register a handler function.

        Args:
            event_type: The event type to handle

        Returns:
            A decorator function
        """
        # Store tasks to prevent garbage collection
        tasks: list[asyncio.Task[None]] = []

        def decorator(handler: T) -> T:
            # Store metadata on the handler
            handler._is_event_handler = True  # type: ignore[attr-defined]
            handler._event_type = event_type  # type: ignore[attr-defined]
            handler._registration_task = None  # type: ignore[attr-defined]

            # If we have a registry, register the handler
            if cls._registry is not None:
                # Create a task to register the handler asynchronously
                task: asyncio.Task[None] = asyncio.create_task(
                    cls._registry.register(event_type, handler)  # type: ignore[arg-type]
                )
                # Store task to prevent garbage collection
                handler._registration_task = task  # type: ignore[attr-defined]
                # Keep a reference to the task to ensure it's awaited
                tasks.append(task)

            return handler

        return decorator  # type: ignore[return-value]


def subscribe(
    event_type: str,
    *,
    logger: LoggerProtocol | None = None,
) -> Callable[[T], T]:
    """Decorator to register an event handler.

    This is a simplified version of the decorator that doesn't depend on an event bus.
    Instead, it uses the HandlerDecorator which will register with the registry when available.

    Args:
        event_type: Type of event to subscribe to
        logger: Optional logger for registration actions

    Returns:
        Decorated handler
    """

    def decorator(handler: T) -> T:
        return HandlerDecorator.handles(event_type)(handler)

    return decorator
