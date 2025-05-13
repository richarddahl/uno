# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Event handling and event-related functionality.

This package provides components for working with events
in an event-driven architecture.
"""

from __future__ import annotations

from uno.events.decorators import HandlerDecorator, subscribe
from uno.events.errors import EventHandlerError
from uno.events.base import DomainEvent
from uno.events.protocols import (
    EventBusProtocol,
    EventHandlerProtocol,
    EventMiddlewareProtocol,
    EventRegistryProtocol,
    DomainEventProtocol,
    EventHandlerRegistryProtocol,
    EventProtocol,
    EventProcessorProtocol,
)
from uno.events.registry import (
    AsyncEventHandlerAdapter,
    EventHandlerRegistry,
    register_event_handler,
)
from uno.events.processor import EventProcessor

__all__ = [
    # Protocols
    "EventBusProtocol",
    "EventHandlerProtocol",
    "EventMiddlewareProtocol",
    "EventRegistryProtocol",
    "DomainEventProtocol",
    "EventHandlerRegistryProtocol",
    "EventProtocol",
    "EventProcessorProtocol",
    # Implementations
    "AsyncEventHandlerAdapter",
    "EventHandlerRegistry",
    "DomainEvent",
    "EventProcessor",
    # Decorators
    "HandlerDecorator",
    "subscribe",
    # Errors
    "EventHandlerError",
    # Helper functions
    "register_event_handler",
]
