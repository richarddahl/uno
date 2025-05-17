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
    """
    Protocol defining the interface for loggers in the Uno framework.

    This protocol is NOT runtime_checkable and should be used
    for static type checking only.
    """

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a debug message."""
        ...

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an info message."""
        ...

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a warning message."""
        ...

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an error message."""
        ...

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a critical message."""
        ...

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an exception message."""
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
