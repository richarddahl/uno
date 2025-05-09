# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Public API for the Uno events package.

This module exports the public API for event sourcing in the Uno framework,
providing domain events, event bus, and event store capabilities.
"""

# Core protocols
from uno.events.protocols import (
    EventBusProtocol,
    EventPublisherProtocol,
    EventStoreProtocol,
    EventHandler,
    EventHandlerMiddleware,
    CommandHandler,
)

# Base event types
from uno.events.base_event import DomainEvent
from uno.events.deleted_event import DeletedEvent
from uno.events.restored_event import RestoredEvent

# Configuration and helpers
from uno.events.config import EventsConfig
from uno.events.context import EventContext
from uno.events.priority import EventPriority
from uno.events.factory import get_event_bus, get_event_publisher, get_event_store
from uno.events.registry import register_event_handler, subscribe

# In-memory implementations
from uno.events.implementations.bus import InMemoryEventBus
from uno.events.implementations.store import InMemoryEventStore

# Handler utilities
from uno.events.handlers import (
    EventHandlerContext,
    EventHandlerDecorator,
    EventHandlerRegistry,
    LoggingMiddleware,
    TimingMiddleware,
    discover_handlers,
    handles,
)

# Middleware
from uno.events.middleware import (
    CircuitBreakerMiddleware,
    CircuitBreakerState,
    EventMetrics,
    MetricsMiddleware,
    RetryMiddleware,
    RetryOptions,
)

# Errors
from uno.events.errors import (
    EventErrorCode,
    EventError,
    EventPublishError,
    EventSubscribeError,
    EventHandlerError,
    EventSerializationError,
    EventDeserializationError,
    EventUpcastError,
    EventDowncastError,
)

__all__ = [
    # Core protocols
    "EventBusProtocol",
    "EventPublisherProtocol",
    "EventStoreProtocol",
    "EventHandler",
    "EventHandlerMiddleware",
    "CommandHandler",
    # Base event types
    "DomainEvent",
    "DeletedEvent",
    "RestoredEvent",
    # Configuration and helpers
    "EventsConfig",
    "EventContext",
    "EventPriority",
    "get_event_bus",
    "get_event_publisher",
    "get_event_store",
    "register_event_handler",
    "subscribe",
    # In-memory implementations
    "InMemoryEventBus",
    "InMemoryEventStore",
    # Handler utilities
    "EventHandlerContext",
    "EventHandlerDecorator",
    "EventHandlerRegistry",
    "LoggingMiddleware",
    "TimingMiddleware",
    "discover_handlers",
    "handles",
    # Middleware
    "CircuitBreakerMiddleware",
    "CircuitBreakerState",
    "EventMetrics",
    "MetricsMiddleware",
    "RetryMiddleware",
    "RetryOptions",
    # Errors
    "EventErrorCode",
    "EventError",
    "EventPublishError",
    "EventSubscribeError",
    "EventHandlerError",
    "EventSerializationError",
    "EventDeserializationError",
    "EventUpcastError",
    "EventDowncastError",
]
