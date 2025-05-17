# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Enhanced error logging that integrates with Uno's custom logger functionality.

This module bridges the base error logging functionality with Uno's
structured logging system.
"""

import asyncio
import traceback
from typing import Any

from uno.errors import ErrorSeverity
from uno.logging.errors import LoggingError
from uno.logging.logger import get_logger


class EnhancedErrorLogger:
    """Logger that integrates with Uno's custom logging system."""

    def __init__(self, name: str = "enhanced_error_logger") -> None:
        """Initialize an enhanced error logger with the given name.

        Args:
            name: The name of the logger
        """
        self.logger = get_logger(name)

    async def log_error(
        self,
        error: Exception,
        severity: ErrorSeverity | str = ErrorSeverity.ERROR,
        additional_context: dict[str, Any] | None = None,
    ) -> None:
        """Log an error asynchronously.

        Args:
            error: The exception to log
            severity: The severity level for this error
            additional_context: Any additional context to include in the log
        """
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None, self._log_error, error, severity, additional_context
        )

    def _log_error(
        self,
        error: Exception,
        severity: ErrorSeverity | str = ErrorSeverity.ERROR,
        additional_context: dict[str, Any] | None = None,
    ) -> None:
        """Synchronous implementation of error logging.

        Args:
            error: The exception to log
            severity: The severity level for this error
            additional_context: Any additional context to include in the log
        """
        # Convert string severity to enum if needed
        if isinstance(severity, str):
            try:
                severity = ErrorSeverity(severity)
            except ValueError:
                # Default to ERROR if string doesn't match any enum value
                severity = ErrorSeverity.ERROR

        context = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exception(
                type(error), error, error.__traceback__
            ),
            "severity": severity.value,
        }

        if additional_context:
            context.update(additional_context)

        log_method = getattr(self.logger, severity.value, self.logger.error)
        log_method(f"Error occurred: {error}", extra=context)


def get_enhanced_error_logger(
    name: str = "enhanced_error_logger",
) -> EnhancedErrorLogger:
    """Get an enhanced error logger instance.

    Args:
        name: The name for the error logger

    Returns:
        An instance of EnhancedErrorLogger
    """
    return EnhancedErrorLogger(name)
