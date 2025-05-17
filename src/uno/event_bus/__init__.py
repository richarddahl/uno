"""Event bus implementation for the Uno framework.

This module provides an event bus implementation that supports:
- Publish/subscribe pattern
- Middleware support
- Durable subscriptions
- Retry policies for failed event processing
- Metrics collection and monitoring
"""

from typing import TypeVar

from uno.domain.protocols import DomainEventProtocol

from .base import EventBus
from .durable_bus import DurableEventBus
from .metrics_integration import EventBusMetrics, MetricsMiddleware
from .metrics import LoggingMiddleware, TimingMiddleware  # type: ignore[attr-defined]
from .protocols import EventBusProtocol, EventHandlerProtocol, EventMiddlewareProtocol

# Re-export types for convenience
E = TypeVar("E", bound=DomainEventProtocol)

__all__ = [
    "DurableEventBus",
    "EventBus",
    "EventBusMetrics",
    "EventBusProtocol",
    "EventHandlerProtocol",
    "EventMiddlewareProtocol",
    "LoggingMiddleware",
    "MetricsMiddleware",
    "TimingMiddleware",
]
