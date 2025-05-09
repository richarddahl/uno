# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Base error classes and utilities for the Uno error handling framework.

This module provides the foundation for structured error handling with
error codes, contextual information, and error categories.
"""

import traceback
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class ErrorCategory(Enum):
    """Categories of errors for classification."""

    INTERNAL = auto()  # Internal errors
    DI = auto()  # Dependency injection errors
    DB = auto()  # Database errors
    API = auto()  # API errors
    CONFIG = auto()  # Configuration errors
    EVENT = auto()  # Event handling errors
    VALIDATION = auto()  # Validation errors


class ErrorSeverity(Enum):
    """Severity levels for errors."""

    INFO = auto()  # Informational message, not an error
    WARNING = auto()  # Warning that might need attention
    ERROR = auto()  # Error that affects operation but not critical
    CRITICAL = auto()  # Critical error that prevents core functionality
    FATAL = auto()  # Fatal error that requires system shutdown


@dataclass
class ErrorContext:
    """Context information for an error instance.

    This lightweight class stores contextual information about an error occurrence.
    It's designed to be attached to errors and used for logging and debugging.
    """

    category: ErrorCategory
    severity: ErrorSeverity = ErrorSeverity.ERROR
    code: str = "UNKNOWN"
    details: dict[str, Any] = None

    def __post_init__(self) -> None:
        """Initialize the error context with default values."""
        # Ensure details is a dictionary
        # if it's not already set
        if self.details is None:
            self.details = {}

    def add_detail(self, key: str, value: Any) -> None:
        """Add additional context detail to the error."""
        if self.details is None:
            self.details = {}
        self.details[key] = value


class ErrorCode:
    """
    Error code constants and utilities.

    This class provides standardized error codes and utilities
    for working with them.
    """

    # Core error codes
    UNKNOWN_ERROR = "CORE-0001"


class UnoError(Exception):
    """
    Base class for all Uno framework errors.

    This class provides standardized error formatting with error codes,
    contextual information, and stacktrace capture.
    """

    def __init__(
        self,
        message: str,
        error_code: str = None,
        category: ErrorCategory = ErrorCategory.INTERNAL,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        **details: Any,
    ):
        # Only pass the message to Exception
        super().__init__(message)
        self.message: str = message
        self.error_code: str = error_code or "UNKNOWN"
        self.context = ErrorContext(
            category=category,
            severity=severity,
            code=self.error_code,
            details=details if details else None,
        )

        # Capture stacktrace
        self.traceback: str = "".join(
            traceback.format_exception(*traceback.sys.exc_info())
        )

        # Store the original cause if this wraps another exception
        self.original_cause = None
        if cause := self.__cause__:
            self.original_cause = cause
            # Add original error details to context
            self.context.add_detail("original_error", str(cause))
            self.context.add_detail("original_error_type", type(cause).__name__)

    def __str__(self) -> str:
        """Get string representation of error."""
        return f"{self.error_code}: {self.message}"

    def with_detail(self, key: str, value: Any) -> "UnoError":
        """Add detail to error context and return self for chaining."""
        self.context.add_detail(key, value)
        return self
