# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Command handling for the Uno framework.

This module provides the core components for command handling in a
CQRS/DDD architecture.
"""

from __future__ import annotations
from typing import Any, Callable, TypeVar

from uno.commands.base_command import Command
from uno.commands.errors import CommandNotFoundError, CommandDispatchError
from uno.commands.protocols import CommandHandlerProtocol

C = TypeVar("C", bound=Command)
T = TypeVar("T")


class CommandBus:
    """
    Command bus for dispatching commands to their handlers.

    Supports middleware and DI integration.
    """

    def __init__(self) -> None:
        """Initialize a new command bus."""
        self._handlers: dict[type[Command], CommandHandlerProtocol] = {}
        self._middleware: list[Callable] = []

    def register_handler(
        self, command_type: type[Command], handler: CommandHandlerProtocol
    ) -> None:
        """
        Register a handler for a specific command type.

        Args:
            command_type: The type of command to register a handler for
            handler: The handler that will process the command
        """
        self._handlers[command_type] = handler

    def add_middleware(self, middleware: Callable) -> None:
        """
        Add middleware to the command processing pipeline.

        Args:
            middleware: The middleware function to add
        """
        self._middleware.append(middleware)

    async def dispatch(self, command: Command) -> Any:
        """
        Dispatch a command to its registered handler.

        Args:
            command: The command to dispatch

        Returns:
            The result of the command handler

        Raises:
            CommandNotFoundError: If no handler is registered for the command type
            CommandDispatchError: If there's an error dispatching the command
        """
        command_type = type(command)
        if command_type not in self._handlers:
            raise CommandNotFoundError(command_type.__name__)

        handler = self._handlers[command_type]

        # Apply middleware (if any)
        result = handler.handle
        for mw in reversed(self._middleware):
            result = mw(result)

        try:
            return await result(command)
        except Exception as e:
            raise CommandDispatchError(f"Error while dispatching command: {e}") from e
