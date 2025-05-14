# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Base error classes and utilities for the Uno error handling system.

This module provides the foundation for structured error handling with
error codes, contextual information, and error categories.
"""

from datetime import UTC, datetime
from enum import Enum, auto
import inspect
import os
from typing import Any
import copy


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


class ErrorSeverity(str, Enum):
    """Severity levels for errors across Uno (logging, domain, infra, etc)."""
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    FATAL = "fatal"


class UnoError(Exception):
    """
    Base error class for Uno errors.
    Should only be subclassed for package-specific errors, not instantiated directly.
    """

    def add_context(self, key: str, value: Any) -> "UnoError":
        """Add a key-value pair to the error context and return self for chaining."""
        if not hasattr(self, "context") or self.context is None:
            self.context = {}
        self.context[key] = value
        return self

    def __new__(cls, *args: Any, **kwargs: Any) -> "UnoError":
        if cls is UnoError:
            raise TypeError(
                "Do not instantiate UnoError directly; subclass it for specific errors."
            )
        return super().__new__(cls)

    def __init__(
        self,
        code: str,
        message: str,
        category: ErrorCategory,
        severity: ErrorSeverity,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a new UnoError (never instantiate directly).

        Args:
            code: Unique identifier for this error type
            message: Human-readable error message
            category: Category the error belongs to
            severity: Severity level of the error
            context: Additional contextual information
            **kwargs: Ignored. Accepts arbitrary keyword arguments for subclass compatibility and error context propagation. This allows error subclasses to propagate extra context (e.g., timestamp) safely.
        """
        self.code = code
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.timestamp = datetime.now(UTC)

    def with_context(self, context: dict[str, Any]) -> "UnoError":
        """Return a new error with additional context."""
        # Create a new instance with the same class, copying all attributes
        new_error = copy.copy(self)
        # Just update the context attribute
        new_error.context = {**self.context, **context}
        return new_error

    @classmethod
    def wrap(
        cls,
        exception: Exception,
        code: str,
        message: str,
        category: ErrorCategory,
        severity: ErrorSeverity,
        context: dict[str, Any] | None = None,
    ) -> "UnoError":
        """
        Wrap an exception with a UnoError, always including the exception type in context.

        Args:
            exception: The exception to wrap
            code: Unique identifier for this error type
            message: Human-readable error message
            category: Category the error belongs to
            severity: Severity level of the error
            context: Additional contextual information

        Returns:
            New UnoError instance wrapping the exception
        """
        merged_context = dict(context) if context else {}
        if "original_exception" not in merged_context:
            merged_context["original_exception"] = type(exception).__name__
        err = cls(code, message, category, severity, merged_context)
        err.__cause__ = exception
        return err

    def __str__(self) -> str:
        """Get string representation of the error.

        Returns:
            String in format 'code: message'
        """
        return f"{self.code}: {self.message}"

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the error.

        Returns:
            Dictionary with all error properties
        """
        return {
            "code": self.code,
            "message": self.message,
            "category": self.category.name,
            "severity": self.severity.name,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
        }


def get_error_context() -> dict[str, Any]:
    """
    Get context information about where an error occurred.

    Returns contextual information about the calling frame including:
    - file_name: The name of the file
    - line_number: The line number where the error occurred
    - function_name: The name of the function where the error occurred
    - timestamp: The UTC timestamp when the error occurred

    Returns:
        dict[str, Any]: A dictionary with error context information
    """
    # Get the frame 1 level up (caller of this function)
    current_frame = inspect.currentframe()
    if current_frame is None:
        # If we can't get a frame (rare but possible), return minimal context
        return {
            "file_name": "unknown",
            "line_number": 0,
            "function_name": "unknown",
            "timestamp": datetime.now(UTC).isoformat(),
        }

    caller_frame = current_frame.f_back
    if caller_frame is None:
        # This would be very unusual, but let's handle it anyway
        return {
            "file_name": "unknown",
            "line_number": 0,
            "function_name": "unknown",
            "timestamp": datetime.now(UTC).isoformat(),
        }
    frame_info = inspect.getframeinfo(caller_frame)

    # Extract relevant information
    file_name = os.path.basename(frame_info.filename)
    line_number = frame_info.lineno
    function_name = frame_info.function

    # Create and return the context dictionary
    return {
        "file_name": file_name,
        "line_number": line_number,
        "function_name": function_name,
        "timestamp": datetime.now(UTC).isoformat(),
    }
