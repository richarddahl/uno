# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Public API for the Uno error handling system.

This module exports the public API for the Uno error handling system, including
the base error classes, utilities, and middleware.
"""
from typing import Any

from uno.errors.base import ErrorCategory, ErrorContext, ErrorSeverity, UnoError
from uno.errors.logging import ErrorLogger
from uno.errors.middleware import ErrorMiddleware

__all__ = [
    "ErrorCategory",
    "ErrorContext",
    # Logging utilities
    "ErrorLogger",
    # Middleware
    "ErrorMiddleware",
    "ErrorSeverity",
    # Core error types
    "UnoError",
    # Factory functions
    "create_error",
    "wrap_exception",
]


def create_error(
    message: str,
    error_code: str = "UNKNOWN",
    category: ErrorCategory = ErrorCategory.INTERNAL,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    **details: Any,
) -> UnoError:
    """
    Create a UnoError with the given parameters.

    This factory function makes it easy to create UnoErrors with a consistent format.

    Args:
        message: The error message
        error_code: The error code
        category: The error category
        severity: The error severity
        **details: Additional details to include in the error context

    Returns:
        A UnoError instance
    """
    return UnoError(
        message=message,
        error_code=error_code,
        category=category,
        severity=severity,
        **details,
    )


def wrap_exception(
    exception: Exception,
    message: str | None = None,
    error_code: str = "WRAPPED_ERROR",
    category: ErrorCategory = ErrorCategory.INTERNAL,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    **details: Any,
) -> UnoError:
    """
    Wrap an existing exception in a UnoError.

    This function creates a UnoError that wraps another exception, preserving
    the original exception as the cause.

    Args:
        exception: The exception to wrap
        message: The error message (defaults to str(exception) if None)
        error_code: The error code
        category: The error category
        severity: The error severity
        **details: Additional details to include in the error context

    Returns:
        A UnoError instance with the original exception as the cause
    """
    if message is None:
        message = str(exception)

    # Create error with original exception as cause
    error = UnoError(
        message=message,
        error_code=error_code,
        category=category,
        severity=severity,
        exception_type=type(exception).__name__,
        **details,
    )

    # Set the original exception as the cause
    error.__cause__ = exception

    return error
