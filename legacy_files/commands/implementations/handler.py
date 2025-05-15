# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
In-memory command handling implementation.

This module provides a simple in-memory implementation of the command bus
for testing and simple applications.
"""

from __future__ import annotations
from typing import Any

from uno.commands.base_command import Command
from uno.commands.handler import CommandBus
from uno.logging.protocols import LoggerProtocol


class InMemoryCommandBus(CommandBus):
    """
    Simple in-memory command bus implementation (development/testing).

    This implementation logs all commands and their results but otherwise
    behaves the same as the base CommandBus.
    """

    def __init__(self, logger: LoggerProtocol) -> None:
        """
        Initialize the in-memory command bus.

        Args:
            logger: Logger instance for structured logging
        """
        super().__init__()
        self.logger = logger

    async def dispatch(self, command: Command) -> Any:
        """
        Dispatch a command to its registered handler with logging.

        Args:
            command: The command to dispatch

        Returns:
            The result of the command handler
        """
        command_type = type(command).__name__
        command_id = getattr(command, "command_id", None)

        await self.logger.info(
            "Dispatching command",
            command_type=command_type,
            command_id=command_id,
            command=self._command_to_dict(command),
        )

        try:
            result = await super().dispatch(command)

            await self.logger.info(
                "Command handled successfully",
                command_type=command_type,
                command_id=command_id,
            )

            return result
        except Exception as e:
            await self.logger.error(
                "Command handling failed",
                command_type=command_type,
                command_id=command_id,
                error=str(e),
                exc_info=True,
            )
            raise

    def _command_to_dict(self, command: Command) -> dict:
        """
        Convert a command to a dictionary for logging.

        Args:
            command: The command to convert

        Returns:
            Dictionary representation of the command
        """
        if hasattr(command, "model_dump"):
            return command.model_dump(
                exclude_none=True, exclude_unset=True, by_alias=True
            )
        elif hasattr(command, "to_dict"):
            return command.to_dict()
        return {k: v for k, v in command.__dict__.items() if not k.startswith("_")}
