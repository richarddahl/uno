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
    """
    Categories of errors for classification.

    These categories help classify errors for appropriate handling
    and reporting.
    """

    INTERNAL = auto()  # Internal errors
    DI = auto()  # Dependency injection errors


class ErrorSeverity(Enum):
    """
    Severity levels for errors.

    These severity levels help prioritize error handling and reporting.
    """

    INFO = auto()  # Informational message, not an error
    WARNING = auto()  # Warning that might need attention
    ERROR = auto()  # Error that affects operation but not critical
    CRITICAL = auto()  # Critical error that prevents core functionality
    FATAL = auto()  # Fatal error that requires system shutdown


@dataclass(frozen=True)
class ErrorInfo:
    """
    Information about an error code.

    This class stores metadata about error codes for documentation
    and consistent handling.
    """

    code: str
    message_template: str
    category: ErrorCategory
    severity: ErrorSeverity
    description: str
    http_status_code: int | None = None
    retry_allowed: bool = True


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

    def __init__(self, message: str, error_code: str, **context: Any):
        # Only pass the message to Exception, never keyword arguments
        super().__init__(message)
        self.message: str = message
        self.error_code: str = error_code
        self.traceback: str = "".join(
            traceback.format_exception(*traceback.sys.exc_info())
        )

    def __str__(self) -> str:
        """Get string representation of error."""
        return f"{self.error_code}: {self.message}"
