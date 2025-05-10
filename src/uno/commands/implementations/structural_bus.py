# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
In-memory command bus implementation.

This module provides an in-memory implementation of the command bus
with proper structural typing and following Uno idioms.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, TYPE_CHECKING

from uno.commands.base_command import Command
from uno.commands.errors import CommandNotFoundError, CommandDispatchError

if TYPE_CHECKING:
    from uno.commands.protocols import CommandHandlerProtocol
    from uno.logging.protocols import LoggerProtocol

C = TypeVar("C", bound=Command)  # Command type
T = TypeVar("T")  # Return type

# Type aliases for better readability
MiddlewareType = Callable[[Callable[[C], Awaitable[T]]], Callable[[C], Awaitable[T]]]


class StructuralCommandBus:
    """
    A command bus implementation using structural typing.

    This implementation follows Uno's idioms of using structural typing
    rather than protocol inheritance.
    """

    def __init__(self, logger: LoggerProtocol) -> None:
        """
        Initialize the command bus.

        Args:
            logger: Logger service for logging command execution
        """
        self.logger = logger
        self._handlers: dict[type, "CommandHandlerProtocol"] = {}
        self._middleware: list[MiddlewareType] = []

    def register_handler(
        self, command_type: type, handler: "CommandHandlerProtocol"
    ) -> None:
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

    async def dispatch(self, command: C) -> Any:
        """
        Dispatch a command to its registered handler.

        Args:
            command: The command to dispatch

        Returns:
            The handler result

        Raises:
            CommandNotFoundError: If no handler is registered for the command type
            CommandDispatchError: If there's an error dispatching the command
        """
        command_type = type(command)
        if command_type not in self._handlers:
            self.logger.error(
                "No handler registered for command",
                command_type=command_type.__name__,
            )
            raise CommandNotFoundError(command_type.__name__)

        handler = self._handlers[command_type]
        self.logger.info(
            "Dispatching command",
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
                "Error executing command",
                command_type=command_type.__name__,
                error=str(e),
            )
            raise CommandDispatchError(f"Error while dispatching command: {e}") from e
