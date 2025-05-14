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
from contextlib import contextmanager, asynccontextmanager
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Protocol,
    TypeVar,
    runtime_checkable,
)

if TYPE_CHECKING:
    from collections.abc import Generator, AsyncGenerator
    from types import TracebackType

@runtime_checkable
class ContextProtocol(Protocol):
    """Protocol for managing context data in the logging system."""

    def get_context(self) -> dict[str, Any]:
        """Get the current context data."""
        ...



    def set_context(self, context: dict[str, Any]) -> None:
        """Set the current context data."""
        ...



    def update_context(self, **kwargs: Any) -> None:
        """Update the current context data with new values."""
        ...



    @contextmanager
    def context_scope(self, **kwargs: Any) -> Generator[None]:
        """Create a context scope that will be automatically cleaned up."""
        ...



    @asynccontextmanager
    async def async_context_scope(self, **kwargs: Any) -> AsyncGenerator[None]:
        """Create an async context scope that will be automatically cleaned up."""
        ...





@runtime_checkable
class LoggerScopeProtocol(Protocol):
    """Protocol for logger scope/context management in Uno logging system."""

    async def scope(self, name: str) -> Any:
        """Async context manager for logger scope. Yields a logger scope/context object."""
        ...

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
    """Protocol defining the interface for all loggers in the Uno framework.

    Supports async context management for resource setup and teardown.
    """

    async def __aenter__(self) -> LoggerProtocol:
        """Enter the async context manager.

        Returns:
            LoggerProtocol: The logger instance (self).
        """
        ...



    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Exit the async context manager.

        Args:
            exc_type: Exception type, if raised
            exc: Exception instance, if raised
            tb: Traceback, if exception raised
        """
        ...



    async def debug(self, message: str, **kwargs: Any) -> None:
        """Log a debug message asynchronously.

        Args:
            message: Log message
            **kwargs: Additional context data
        """
        ...



    async def info(self, message: str, **kwargs: Any) -> None:
        """Log an info message asynchronously.

        Args:
            message: Log message
            **kwargs: Additional context data
        """
        ...



    async def warning(self, message: str, **kwargs: Any) -> None:
        """Log a warning message asynchronously.

        Args:
            message: Log message
            **kwargs: Additional context data
        """
        ...



    async def error(self, message: str, **kwargs: Any) -> None:
        """Log an error message asynchronously.

        Args:
            message: Log message
            **kwargs: Additional context data
        """
        ...



    async def structured_log(self, level: LogLevel, message: str, **kwargs: Any) -> None:
        """Log a structured message with level and context asynchronously.

        Args:
            level: Log level
            message: Log message
            **kwargs: Additional context data
        """
        ...



    async def critical(self, message: str, **kwargs: Any) -> None:
        """Log a critical message asynchronously.

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
    def context(self, **kwargs: Any) -> Generator[None]:
        """Add context information to all logs within this context.

        This creates a context manager that adds the provided context
        information to all logs emitted within its scope.

        Args:
            **kwargs: Context key-value pairs

        Yields:
            None
        """
        ...



    @asynccontextmanager
    async def async_context(self, **kwargs: Any) -> AsyncGenerator[None]:
        """Add context information to all logs within this async context.

        This creates an async context manager that adds the provided context
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


