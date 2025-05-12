"""
Structured logging middleware for error handling.

This module provides middleware for capturing and logging errors with structured
context and correlation IDs. It integrates with the error context system to
provide consistent error handling across the application.
"""

import asyncio
import logging
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any, TypeVar, TYPE_CHECKING

from structlog.types import EventDict, Processor

from uno.logging.logger import get_logger
from uno.core.tracing import get_trace_context

from .base import UnoError
from .context import get_current_context

if TYPE_CHECKING:
    from .metrics import ErrorMetrics

# Type variable for generic error types
E = TypeVar("E", bound=Exception)

# Context variable for correlation ID
correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)

# Global logger instance
logger = get_logger("uno.errors")


def get_correlation_id() -> str:
    """Get the current correlation ID or generate a new one.

    Returns:
        str: The current correlation ID or a new UUID4
    """
    if (cid := correlation_id_ctx.get()) is None:
        cid = str(uuid.uuid4())
        correlation_id_ctx.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    """Set the current correlation ID.

    Args:
        cid: The correlation ID to set
    """
    correlation_id_ctx.set(cid)


def add_correlation_id(_: logging.Logger, __: str, event_dict: EventDict) -> EventDict:
    """Add correlation ID to log entries.

    Args:
        _: The logger instance
        __: The log method name
        event_dict: The event dictionary to modify

    Returns:
        The modified event dictionary with correlation ID
    """
    event_dict["correlation_id"] = get_correlation_id()
    return event_dict


def add_error_context(_: logging.Logger, __: str, event_dict: EventDict) -> EventDict:
    """Add error context to log entries.

    Args:
        _: The logger instance
        __: The log method name
        event_dict: The event dictionary to modify

    Returns:
        The modified event dictionary with error context
    """
    if "error" in event_dict and isinstance(event_dict["error"], Exception):
        error = event_dict["error"]
        if isinstance(error, UnoError):
            event_dict["error_code"] = getattr(error, "code", None)
            event_dict["error_category"] = getattr(error, "category", None)
            event_dict["error_severity"] = getattr(error, "severity", None)

            # Add context from the error
            context = getattr(error, "context", {})
            if context:
                event_dict["error_context"] = context

    # Add current context
    current_ctx = get_current_context()
    if current_ctx:
        event_dict["context"] = current_ctx

    return event_dict


class ErrorLogger:
    """Structured error logger with correlation ID support."""

    def __init__(self, name: str = "uno.errors"):
        """Initialize the error logger.

        Args:
            name: The logger name
        """
        self.logger = get_logger(name)
        self._bound_context: dict[str, Any] = {}
        self.name = name  # For testing purposes

    def bind_context(self, **context: Any) -> 'ErrorLogger':
        """Bind context to the logger.

        Args:
            **context: Context to bind

        Returns:
            A new logger instance with the bound context
        """
        new_logger = ErrorLogger(self.name)
        new_logger._bound_context = {**self._bound_context, **context}
        return new_logger

    async def error(
        self,
        message: str,
        error: Exception | None = None,
        **context: Any,
    ) -> None:
        """Log an error with context.

        Args:
            message: The error message
            error: The exception that caused the error
            **context: Additional context
        """
        log_context: dict[str, Any] = {
            "event": message,
            "level": "error",
            **context,
        }
        if error is not None:
            log_context["error"] = error
        await self.logger.error(message, **log_context)

    async def warning(
        self,
        message: str,
        **context: Any,
    ) -> None:
        """Log a warning with context.

        Args:
            message: The warning message
            **context: Additional context
        """
        log_context: dict[str, Any] = {
            "event": message,
            "level": "warning",
            **context,
        }
        await self.logger.warning(**log_context)

    async def critical(
        self,
        message: str,
        **context: Any,
    ) -> None:
        """Log a critical message with context.

        Args:
            message: The critical message
            **context: Additional context
        """
        log_context: dict[str, Any] = {
            "event": message,
            "level": "critical",
            **context,
        }
        await self.logger.critical(**log_context)

    async def exception(
        self,
        message: str,
        error: Exception,
        **context: Any,
    ) -> None:
        """Log an exception with context.

        Args:
            message: The error message
            error: The exception that was raised
            **context: Additional context
        """
        log_context: dict[str, Any] = {
            "event": message,
            "level": "error",
            **context,
        }
        await self.logger.exception(
            message,
            error=error,
            **{k: v for k, v in log_context.items() if k != "error"},
        )


class LoggingMiddleware:
    """Middleware for structured error logging with metrics and correlation.

    This middleware integrates with the error handling system to provide:
    - Structured error logging with context
    - Correlation ID propagation
    - Error metrics collection
    - Integration with the error context system
    """

    def __init__(
        self,
        logger: ErrorLogger | None = None,
        metrics: 'ErrorMetrics | None' = None,
        record_metrics: bool = True,
    ) -> None:
        """Initialize the middleware.

        Args:
            logger: The error logger to use. If None, a default logger will be created.
            metrics: Optional metrics collector for error tracking
            record_metrics: Whether to record error metrics
        """
        self.logger = logger or ErrorLogger()
        self.metrics = metrics
        self.record_metrics = record_metrics

    async def __call__(self, error: Exception) -> None:
        """Process an error.

        This method is called when an error occurs in the event processing pipeline.
        It enriches the error with context, records metrics, and logs the error.

        Args:
            error: The error to process
        """
        if not isinstance(error, Exception):
            return

        # Generate a unique error ID for correlation
        error_id = str(uuid.uuid4())

        # Get current context and correlation ID
        current_context = get_current_context() or {}
        correlation_id = current_context.get("correlation_id") or get_correlation_id()

        # Get distributed tracing context
        trace_ctx = get_trace_context()

        # Prepare error context
        error_context = {
            "event": "Error processed",
            "error_id": error_id,
            "correlation_id": correlation_id,
            "trace_id": trace_ctx.get("trace_id"),
            "span_id": trace_ctx.get("span_id"),
            "parent_span_id": trace_ctx.get("parent_span_id"),
            "error_type": error.__class__.__name__,
            "module": error.__class__.__module__,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Add UnoError specific fields if available
        if isinstance(error, UnoError):
            error_context.update(
                {
                    "error_code": getattr(error, "code", None),
                    "category": getattr(error, "category", None),
                    "severity": getattr(error, "severity", None),
                    "original_error": str(getattr(error, "__cause__", None) or ""),
                    "context": getattr(error, "context", {}),
                }
            )

        # Log the error with enriched context
        message = f"{error_id}: {str(error) or 'No error message'}"
        log_context: dict[str, Any] = {
            **error_context,
            "error": error,
            "context": current_context,
        }

        # Record error metrics if enabled
        metrics_failed = False
        if self.record_metrics and self.metrics is not None:
            try:
                if asyncio.iscoroutinefunction(self.metrics.record_error):
                    await self.metrics.record_error(error)
                else:
                    self.metrics.record_error(error)
            except Exception as metrics_error:
                metrics_failed = True
                await self.logger.error(
                    "Failed to record error metrics",
                    error=metrics_error,
                    original_error=str(error),
                    level="error"
                )

        # Log at appropriate level based on error severity
        if hasattr(error, "severity"):
            if error.severity == "CRITICAL":
                await self.logger.critical(message, **log_context)
            elif error.severity == "ERROR":
                await self.logger.error(message, **log_context)
            elif error.severity == "WARNING":
                await self.logger.warning(message, **log_context)
            else:
                await self.logger.error(message, **log_context)
        else:
            await self.logger.error(message, **log_context)


def configure_structured_logging(
    level: int = logging.INFO, json_format: bool = True, **processors: Processor
) -> dict[str, Callable[..., Any]]:
    """Configure structured logging.

    Args:
        level: The logging level
        json_format: Whether to use JSON format
        **processors: Additional log processors

    Returns:
        Dictionary of configured processors
    """
    from structlog import configure
    from structlog.processors import JSONRenderer, TimeStamper, format_exc_info
    from structlog.stdlib import (
        BoundLogger,
        LoggerFactory,
        add_log_level,
        filter_by_level,
    )

    default_processors: list[Processor] = [
        filter_by_level,
        add_log_level,
        add_correlation_id,
        add_error_context,
        TimeStamper(fmt="iso"),
        format_exc_info,
    ]

    if json_format:
        default_processors.append(JSONRenderer())
    else:
        from structlog.dev import ConsoleRenderer

        default_processors.append(ConsoleRenderer())

    # Add any additional processors
    if processors:
        default_processors.extend(processors.values())

    configure(
        processors=default_processors,
        wrapper_class=BoundLogger,
        context_class=dict,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[logging.StreamHandler()],
    )

    return {
        "add_correlation_id": add_correlation_id,  # type: ignore
        "add_error_context": add_error_context,  # type: ignore
    }


# Default error logger
error_logger = ErrorLogger()
