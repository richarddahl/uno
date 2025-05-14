# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework# core_library/logging/interfaces.py

"""
Logging interface definitions for the Uno framework.

This module defines the protocols and interfaces for the logging system,
providing a consistent contract for all logging implementations.
"""

from __future__ import annotations

from contextlib import contextmanager, asynccontextmanager
from typing import (
    TYPE_CHECKING,
    Any,
    Protocol,
)

from uno.logging.level import LogLevel

if TYPE_CHECKING:
    from collections.abc import Generator, AsyncGenerator, AsyncIterator
    from types import TracebackType


class ContextProtocol(Protocol):
    """Protocol for managing context data in the logging system."""

    async def get_context(self) -> dict[str, Any]:
        """Get the current context data."""
        ...

    async def set_context(self, context: dict[str, Any]) -> None:
        """Set the current context data."""
        ...

    async def update_context(self, **kwargs: Any) -> None:
        """Update the current context data with new values."""
        ...

    @asynccontextmanager
    async def context_scope(self, **kwargs: Any) -> AsyncGenerator[None]:
        """Create an async context scope that will be automatically cleaned up."""
        ...


class LoggerScopeProtocol(Protocol):
    """Protocol for logger scope/context management in Uno logging system."""

    async def scope(self, name: str) -> Any:
        """Async context manager for logger scope. Yields a logger scope/context object."""
        ...


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

    async def structured_log(
        self, level: LogLevel, message: str, **kwargs: Any
    ) -> None:
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

    async def set_level(self, level: LogLevel) -> None:
        """Set the logger's level.

        Args:
            level: New logging level
        """
        ...

    @asynccontextmanager
    async def context(self, **kwargs: Any) -> AsyncGenerator[None]:
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


class LoggerFactoryProtocol(Protocol):
    """Protocol for logger factory implementations."""

    async def create_logger(self, name: str) -> LoggerProtocol:
        """Create a new logger instance.

        Args:
            name: The name of the logger to create

        Returns:
            A configured logger instance
        """
        ...

    @asynccontextmanager
    async def scoped_logger(self, name: str) -> AsyncIterator[LoggerProtocol]:
        """Create a scoped logger instance that will be automatically cleaned up.

        Args:
            name: The name of the logger to create

        Yields:
            A scoped logger instance
        """
        ...
