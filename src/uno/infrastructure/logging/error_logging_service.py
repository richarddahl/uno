"""
ErrorLoggingService for Uno: structured error event logging and context propagation.

Integrates with uno.core.errors to log error events in a structured, context-rich way, using the DI logger system.
"""

from __future__ import annotations

from typing import Any

from uno.core.errors.base import FrameworkError
from uno.infrastructure.logging.logger import LoggerService


class ErrorLoggingService:
    """
    Service for structured error event logging and error context propagation.
    Integrates with LoggerService and uno.core.errors.
    """

    def __init__(self, logger_service: LoggerService) -> None:
        self._logger_service = logger_service

    def log_error(
        self,
        error: Exception,
        *,
        context: dict[str, Any] | None = None,
        trace_context: dict[str, Any] | None = None,
    ) -> None:
        """
        Log an error event in a structured way, including error and trace context.
        If error is a FrameworkError, uses its error_code and context.
        """
        error_context = {}
        if isinstance(error, FrameworkError):
            error_context = {
                "error_code": getattr(error, "error_code", None),
                "error_message": str(error),
                **getattr(error, "context", {}),
            }
        else:
            error_context = {
                "error_type": type(error).__name__,
                "error_message": str(error),
            }
        merged_context = context.copy() if context else {}
        merged_context.update(error_context)
        self._logger_service.structured_log(
            "error",
            merged_context.get("error_message", "An error occurred"),
            error_context=error_context,
            trace_context=trace_context,
            **{k: v for k, v in merged_context.items() if k not in error_context},
        )
