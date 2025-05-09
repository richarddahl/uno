# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework# core_library/logging/interfaces.py

"""
Logging interface definitions for the Uno framework.

This module defines the protocols and interfaces for the logging system,
providing a consistent contract for all logging implementations.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    Optional,
    Protocol,
    TypeVar,
    runtime_checkable,
)


# Define standard logging levels
class LogLevel(str, Enum):
    """Standard logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    def to_stdlib_level(self) -> int:
        """Convert to standard library logging level.

        Returns:
            Standard library logging level integer
        """
        return getattr(logging, self.value)

    @classmethod
    def from_string(cls, value: str) -> LogLevel:
        """Convert a string to a LogLevel.

        Args:
            value: String representation of level

        Returns:
            LogLevel enum value

        Raises:
            ValueError: If the string doesn't match a valid level
        """
        try:
            return cls(value.upper())
        except ValueError:
            raise ValueError(f"Invalid log level: {value}")


T = TypeVar("T")


@runtime_checkable
class LoggerProtocol(Protocol):
    """Protocol defining the interface for all loggers in the Uno framework."""

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log a debug message.

        Args:
            message: Log message
            **kwargs: Additional context data
        """
        ...

    def info(self, message: str, **kwargs: Any) -> None:
        """Log an info message.

        Args:
            message: Log message
            **kwargs: Additional context data
        """
        ...

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log a warning message.

        Args:
            message: Log message
            **kwargs: Additional context data
        """
        ...

    def error(self, message: str, **kwargs: Any) -> None:
        """Log an error message.

        Args:
            message: Log message
            **kwargs: Additional context data
        """
        ...

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log a critical message.

        Args:
            message: Log message
            **kwargs: Additional context data
        """
        ...

    def set_level(self, level: LogLevel) -> None:
        """Set the logger's level.

        Args:
            level: New logging level
        """
        ...

    @contextmanager
    def context(self, **kwargs: Any) -> Generator[None, None, None]:
        """Add context information to all logs within this context.

        This creates a context manager that adds the provided context
        information to all logs emitted within its scope.

        Args:
            **kwargs: Context key-value pairs

        Yields:
            None
        """
        ...

    def bind(self, **kwargs: Any) -> LoggerProtocol:
        """Create a new logger with bound context values.

        Args:
            **kwargs: Context values to bind

        Returns:
            New logger instance with bound context
        """
        ...

    def with_correlation_id(self, correlation_id: str) -> LoggerProtocol:
        """Bind a correlation ID to all logs from this logger.

        Args:
            correlation_id: Correlation ID for tracing

        Returns:
            New logger instance with correlation ID
        """
        ...
