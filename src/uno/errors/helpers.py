"""
Helper functions for error handling in the Uno framework.

This module provides utility functions for creating, manipulating,
and handling errors in a consistent way.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Type, TypeVar, cast

from uno.errors.base import ErrorCategory, ErrorSeverity, UnoError

T = TypeVar("T", bound=UnoError)


def create_error(
    message: str,
    error_code: Optional[str] = None,
    category: ErrorCategory = ErrorCategory.INTERNAL,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    error_class: Type[UnoError] = UnoError,
    **context: Any,
) -> UnoError:
    """Create a UnoError with the given parameters.

    Args:
        message: Human-readable error message
        error_code: Unique identifier for this error type
        category: General category for this error
        severity: How severe this error is
        error_class: Specific error class to instantiate
        **context: Additional contextual information about the error

    Returns:
        A new error instance
    """
    return error_class(
        message=message,
        error_code=error_code,
        category=category,
        severity=severity,
        **context,
    )


def wrap_exception(
    exception: Exception,
    message: Optional[str] = None,
    error_code: str = "WRAPPED_ERROR",
    category: ErrorCategory = ErrorCategory.INTERNAL,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    error_class: Type[UnoError] = UnoError,
    **context: Any,
) -> UnoError:
    """Wrap an existing exception in a UnoError.

    This function creates a UnoError that wraps another exception, preserving
    the original exception as the cause.

    Args:
        exception: The exception to wrap
        message: Error message (defaults to str(exception) if None)
        error_code: Error code for the wrapped exception
        category: Error category
        severity: Error severity
        error_class: Specific error class to instantiate
        **context: Additional context information

    Returns:
        A UnoError instance wrapping the original exception
    """
    return error_class.wrap(
        exception=exception,
        message=message,
        error_code=error_code,
        category=category,
        severity=severity,
        **context,
    )


def error_context_from_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract relevant context information from a dictionary.

    This utility helps create standardized context information
    from various data structures.

    Args:
        data: Dictionary containing data to extract context from

    Returns:
        Dictionary with context information
    """
    # Filter out None values and create a shallow copy
    return {k: v for k, v in data.items() if v is not None}
