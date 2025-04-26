# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

# Event sourcing core
from .base_event import DomainEvent
from .bus import EventBus, EventBusProtocol
from .event_store import EventStore, InMemoryEventStore
from .publisher import EventPublisher, EventPublisherProtocol
from .priority import EventPriority
from .registry import register_event_handler, subscribe
from .factory import get_event_bus, get_event_publisher, get_event_store

# Event handlers
from .handlers import (
    EventHandlerContext,
    EventHandler,
    EventHandlerDecorator,
    EventHandlerMiddleware,
    EventHandlerRegistry,
    LoggingMiddleware,
    TimingMiddleware,
    discover_handlers,
    handles,
)

# Unit of Work
from .unit_of_work import (
    UnitOfWork,
    InMemoryUnitOfWork,
    PostgresUnitOfWork,
    execute_in_transaction,
    execute_operations,
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

__all__ = [
    # Event sourcing core
    "DomainEvent",
    "EventBus",
    "EventBusProtocol",
    "EventPublisher",
    "EventPublisherProtocol",
    "EventPriority",
    "EventStore",
    "InMemoryEventStore",
    "CoreEventHandler",  # Aliased from events module
    "get_event_bus",
    "get_event_publisher",
    "get_event_store",
    "register_event_handler",
    "subscribe",
    
    # Event handlers
    "discover_handlers",
    "EventHandler",
    "EventHandlerContext",
    "EventHandlerDecorator",
    "EventHandlerMiddleware",
    "EventHandlerRegistry",
    "handles",
    "LoggingMiddleware",
    "TimingMiddleware",
    
    # Middleware
    "CircuitBreakerMiddleware",
    "CircuitBreakerState",
    "EventMetrics",
    "MetricsMiddleware",
    "RetryMiddleware",
    "RetryOptions",
    
    # Unit of Work
    "execute_in_transaction",
    "execute_operations",
    "InMemoryUnitOfWork",
    "PostgresUnitOfWork",
    "UnitOfWork",
]
