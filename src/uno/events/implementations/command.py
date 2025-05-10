# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
In-memory command bus implementation.

This module provides an in-memory implementation of the command bus for testing
and simple applications.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Generic, TypeVar, TYPE_CHECKING

from uno.errors import UnoError

if TYPE_CHECKING:
    from uno.events.protocols import CommandHandler
    from uno.logging.protocols import LoggerProtocol

C = TypeVar("C")  # Command type
T = TypeVar("T")  # Return type

# Type aliases for better readability
CommandHandlerType = Callable[[C], Awaitable[T]]
MiddlewareType = Callable[[CommandHandlerType[C, T]], CommandHandlerType[C, T]]


class InMemoryCommandBus(Generic[C, T]):
    """
    An in-memory implementation of the command bus for testing and simple applications.
    """

    def __init__(self, logger: LoggerProtocol) -> None:
        """
        Initialize the in-memory command bus.

        Args:
            logger: Logger service for logging command execution
        """
        self.logger = logger
        self._handlers: dict[type, CommandHandler[C, T]] = {}
        self._middleware: list[MiddlewareType[C, T]] = []

    def register_handler(self, command_type: type, handler: CommandHandler) -> None:
        """
        Register a handler for a specific command type.

        Args:
            command_type: The type of command to handle
            handler: The handler to register
        """
        self._handlers[command_type] = handler

    def add_middleware(self, middleware: Callable) -> None:
        """
        Add middleware to the command processing pipeline.

        Args:
            middleware: The middleware function to add
        """
        self._middleware.append(middleware)

    async def dispatch(self, command: C) -> T:
        """
        Dispatch a command to its registered handler.

        Args:
            command: The command to dispatch

        Returns:
            The handler result

        Raises:
            UnoError: If no handler is registered or if command execution fails
        """
        command_type = type(command)
        if command_type not in self._handlers:
            self.logger.error(
                f"No handler registered for command type {command_type.__name__}",
                command_type=command_type.__name__,
            )
            raise UnoError(
                f"No handler registered for command type {command_type.__name__}",
                error_code="CMD-0001",
                command_type=command_type.__name__
            )

        handler = self._handlers[command_type]
        self.logger.info(
            f"Dispatching command {command_type.__name__}",
            command_type=command_type.__name__,
            handler=handler.__class__.__name__,
        )

        # Apply middleware (if any)
        result = handler.handle
        for mw in reversed(self._middleware):
            result = mw(result)

        try:
            return await result(command)
        except Exception as e:
            self.logger.error(
                f"Error executing command {command_type.__name__}",
                command_type=command_type.__name__,
                error=str(e),
            )
            raise UnoError(
                f"Failed to execute command {command_type.__name__}: {str(e)}",
                error_code="CMD-0002",
                command_type=command_type.__name__,
                error=str(e)
            ) from e
