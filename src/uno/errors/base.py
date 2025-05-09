# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Base error classes and utilities for the Uno error handling system.

This module provides the foundation for structured error handling with
error codes, contextual information, and error categories.
"""

from __future__ import annotations

import traceback
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, TypeVar

T = TypeVar("T", bound="UnoError")


class ErrorCategory(Enum):
    """Categories of errors for classification."""

    INTERNAL = auto()  # Internal/unknown errors
    CONFIG = auto()  # Configuration errors
    DI = auto()  # Dependency injection errors
    DB = auto()  # Database errors
    API = auto()  # API errors
    EVENT = auto()  # Event handling errors
    VALIDATION = auto()  # Validation errors
    SECURITY = auto()  # Security-related errors


class ErrorSeverity(Enum):
    """Severity levels for errors."""

    INFO = auto()  # Informational message, not an error
    WARNING = auto()  # Warning that might need attention
    ERROR = auto()  # Error that affects operation but not critical
    CRITICAL = auto()  # Critical error that prevents core functionality
    FATAL = auto()  # Fatal error that requires system shutdown


class UnoError(Exception):
    """Base class for all framework errors with structured context.

    This class extends Python's built-in Exception class with additional
    context information, error categorization, and severity levels.
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        category: ErrorCategory = ErrorCategory.INTERNAL,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        **context: Any,
    ):
        """Initialize a new UnoError.

        Args:
            message: Human-readable error message
            error_code: Unique identifier for this error type
            category: General category for this error
            severity: How severe this error is
            **context: Additional contextual information about the error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "UNKNOWN"
        self.category = category
        self.severity = severity
        self.context: dict[str, Any] = dict(context) if context else {}
        self.timestamp = datetime.now(timezone.utc)

        # Capture stack trace for debugging
        self.stacktrace = "".join(traceback.format_exception(*traceback.sys.exc_info()))

    def add_context(self, key: str, value: Any) -> UnoError:
        """Add additional context to the error.

        Args:
            key: Context information identifier
            value: Context information value

        Returns:
            Self, for method chaining
        """
        self.context[key] = value
        return self  # For method chaining

    def to_dict(self) -> dict[str, Any]:
        """Convert error to a dictionary for serialization.

        Returns:
            Dictionary representation of the error
        """
        return {
            "error_code": self.error_code,
            "message": self.message,
            "category": self.category.name,
            "severity": self.severity.name,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def wrap(
        cls: type[T],
        exception: Exception,
        message: str | None = None,
        error_code: str | None = None,
        category: ErrorCategory = ErrorCategory.INTERNAL,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        **context: Any,
    ) -> T:
        """Wrap an existing exception in a UnoError.

        Args:
            exception: The exception to wrap
            message: Optional message override (defaults to str(exception))
            error_code: Error code for the wrapped exception
            category: Error category
            severity: Error severity
            **context: Additional context information

        Returns:
            A new UnoError instance with the exception as its cause
        """
        if message is None:
            message = str(exception)

        error = cls(
            message=message,
            error_code=error_code or "WRAPPED_ERROR",
            category=category,
            severity=severity,
            original_exception=type(exception).__name__,
            **context,
        )
        error.__cause__ = exception
        return error
