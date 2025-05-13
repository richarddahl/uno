# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Decorator implementation for event handlers.

This module provides decorators for marking functions and classes as event handlers.
"""

from collections.abc import Callable
from typing import Any, ClassVar, TYPE_CHECKING

if TYPE_CHECKING:
    from uno.events.registry import EventHandlerRegistry
    from uno.logging.protocols import LoggerProtocol


class EventHandlerDecorator:
    """
    Decorator for event handlers.

    Provides decorators for easily marking classes and functions as event handlers
    and registering them with the handler registry.
    """

    _registry: ClassVar["EventHandlerRegistry | None"] = None

    @classmethod
    def set_registry(cls, registry: "EventHandlerRegistry") -> None:
        """
        Set the registry to use for decorators.

        Args:
            registry: The registry to use
        """
        cls._registry = registry

    @classmethod
    def get_registry(cls, logger: "LoggerProtocol") -> "EventHandlerRegistry":
        """
        Get the registry, creating it if needed.

        Args:
            logger: Logger for structured logging

        Returns:
            The registry
        """
        if cls._registry is None:
            # Import here to avoid circular imports
            from uno.events.registry import (
                EventHandlerRegistry,
            )

            cls._registry = EventHandlerRegistry(logger)
        return cls._registry

    @classmethod
    def handles(cls, event_type: str) -> Callable[[type[Any]], type[Any]]:
        """
        Decorator to register a handler for an event type.

        Args:
            event_type: The event type to handle

        Returns:
            Decorator function
        """

        def decorator(handler_class: type[Any]) -> type[Any]:
            # Set the event type on the class
            handler_class._event_type = event_type
            handler_class._is_event_handler = True

            # Mark that this class needs to be registered (will be done at runtime)
            return handler_class

        return decorator


# Export the decorator function
handles = EventHandlerDecorator.handles
