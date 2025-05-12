# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Command-specific errors for the Uno framework.

This module contains error types specific to command handling.
"""

from __future__ import annotations
from enum import Enum, auto
from uno.errors import UnoError


class CommandErrorCode(Enum):
    """Error codes for command-related errors."""

    COMMAND_NOT_FOUND = auto()
    COMMAND_HANDLER_ERROR = auto()
    COMMAND_VALIDATION_ERROR = auto()
    COMMAND_DISPATCH_ERROR = auto()


class CommandError(UnoError):
    """Base class for command-related errors."""

    def __init__(
        self,
        message: str,
        code: CommandErrorCode = CommandErrorCode.COMMAND_HANDLER_ERROR,
        **kwargs,
    ) -> None:
        super().__init__(message, **kwargs)
        self.code = code


class CommandHandlerError(CommandError):
    """Error raised when a command handler encounters a problem."""

    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(message, code=CommandErrorCode.COMMAND_HANDLER_ERROR, **kwargs)


class CommandNotFoundError(CommandError):
    """Error raised when no handler is found for a command."""

    def __init__(self, command_type: str, **kwargs) -> None:
        super().__init__(
            f"No handler registered for command type {command_type}",
            code=CommandErrorCode.COMMAND_NOT_FOUND,
            **kwargs,
        )


class CommandValidationError(CommandError):
    """Error raised when a command fails validation."""

    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(
            message, code=CommandErrorCode.COMMAND_VALIDATION_ERROR, **kwargs
        )


class CommandDispatchError(CommandError):
    """Error raised when there's a problem dispatching a command."""

    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(
            message, code=CommandErrorCode.COMMAND_DISPATCH_ERROR, **kwargs
        )
