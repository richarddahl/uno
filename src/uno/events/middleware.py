"""
Canonical event handler middleware implementations for Uno.

This module only exposes canonical event handler middleware:
- RetryMiddleware: Automatically retries failed event handlers
- MetricsMiddleware: Collects metrics about event handler performance
- CircuitBreakerMiddleware: Prevents cascading failures
"""

from uno.events.middleware.circuit_breaker import (
    CircuitBreakerMiddleware,
    CircuitBreakerState,
)
from uno.events.middleware.metrics import EventMetrics, MetricsMiddleware
from uno.events.middleware.retry import RetryMiddleware, RetryOptions

__all__ = [
    "CircuitBreakerMiddleware",
    "CircuitBreakerState",
    "EventMetrics",
    "MetricsMiddleware",
    "RetryMiddleware",
    "RetryOptions",
]
