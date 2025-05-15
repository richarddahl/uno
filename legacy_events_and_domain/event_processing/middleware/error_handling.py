"""
Standard error handling utilities for Uno event-driven systems.

This module provides a standard error handler for event-driven flows, supporting
logging, error enrichment, and metrics. Use with Uno's DI system for integration.

Example usage:
    from uno.events.error_handling import standard_event_error_handler
    from uno.di import inject

    @inject
    async def handle_event(event, error_handler=standard_event_error_handler):
        try:
            ...
        except Exception as exc:
            error_handler(event, EventError(str(exc)), context)
"""

from uno.errors.context import enrich_error
from uno.events.errors import EventError
from uno.errors.metrics import ErrorMetrics
from uno.logging.logger import LoggerProtocol
from uno.errors.context import Context
from typing import Any


def standard_event_error_handler(
    event: Any,
    exc: EventError,
    context: Context,
    logger: LoggerProtocol,
    metrics: ErrorMetrics,
) -> None:
    """Default error handler for event bus and event handlers.

    Args:
        event: The event being processed
        exc: The EventError instance
    """
    # Enrich error with context
    error = enrich_error(exc, context)
    # Log the error using DI-provided logger
    logger.error(f"Error in event {event}: {error}")
    # Record error metric using DI-provided metrics
    metrics.record_error(error)
