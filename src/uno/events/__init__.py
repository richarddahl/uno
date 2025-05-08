# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

# Event sourcing core
from .base_event import DomainEvent
from .bus import EventBus, EventBusProtocol
from .event_store import EventStore, InMemoryEventStore
from .factory import get_event_bus, get_event_publisher, get_event_store

# Event handlers
from .handlers import (
    EventHandler,
    EventHandlerContext,
    EventHandlerDecorator,
    EventHandlerMiddleware,
    EventHandlerRegistry,
    LoggingMiddleware,
    TimingMiddleware,
    discover_handlers,
    handles,
)

# Middleware
from .middleware import (
    CircuitBreakerMiddleware,
    CircuitBreakerState,
    EventMetrics,
    MetricsMiddleware,
    RetryMiddleware,
    RetryOptions,
)
from .priority import EventPriority
from .publisher import EventPublisher, EventPublisherProtocol
from .registry import register_event_handler, subscribe

# Unit of Work
from .unit_of_work import (
    InMemoryUnitOfWork,
    PostgresUnitOfWork,
    UnitOfWork,
    execute_in_transaction,
    execute_operations,
)

__all__ = [
    "CircuitBreakerMiddleware",
    "CircuitBreakerState",
    "CoreEventHandler",
    "DomainEvent",
    "EventBus",
    "EventBusProtocol",
    "EventHandler",
    "EventHandlerContext",
    "EventHandlerDecorator",
    "EventHandlerMiddleware",
    "EventHandlerRegistry",
    "EventMetrics",
    "EventPriority",
    "EventPublisher",
    "EventPublisherProtocol",
    "EventStore",
    "InMemoryEventStore",
    "InMemoryUnitOfWork",
    "LoggingMiddleware",
    "MetricsMiddleware",
    "PostgresUnitOfWork",
    "RetryMiddleware",
    "RetryOptions",
    "TimingMiddleware",
    "UnitOfWork",
    "discover_handlers",
    "execute_in_transaction",
    "execute_operations",
    "get_event_bus",
    "get_event_publisher",
    "get_event_store",
    "handles",
    "register_event_handler",
    "subscribe",
]
