# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Unified event handling for the uno framework.

This package provides an async-first event handling system with
clean interfaces and composable middleware.
"""

from uno.events.decorators import HandlerDecorator, subscribe
from uno.events.errors import EventHandlerError
from uno.events.protocols import (
    EventBusProtocol,
    EventHandlerProtocol,
    EventMiddlewareProtocol,
    EventRegistryProtocol,
)
from uno.events.registry import (
    AsyncEventHandlerAdapter,
    EventHandlerRegistry,
    register_event_handler,
)

__all__ = [
    # Protocols
    "EventBusProtocol",
    "EventHandlerProtocol",
    "EventMiddlewareProtocol",
    "EventRegistryProtocol",
    # Implementations
    "AsyncEventHandlerAdapter",
    "EventHandlerRegistry",
    # Decorators
    "HandlerDecorator",
    "subscribe",
    # Errors
    "EventHandlerError",
    # Helper functions
    "register_event_handler",
]
