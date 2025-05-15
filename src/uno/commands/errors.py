# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Command-specific errors for the Uno framework.

This module contains error types specific to command handling.
"""

from __future__ import annotations

from typing import Any, Final

from uno.errors.base import ErrorCode, ErrorCategory, ErrorSeverity, UnoError

COMMAND = ErrorCategory("COMMAND")
CMD_ERROR: Final = ErrorCode("CMD_ERROR", COMMAND)
CMD_NOT_FOUND: Final = ErrorCode("CMD_NOT_FOUND", COMMAND)
CMD_HANDLER: Final = ErrorCode("CMD_HANDLER", COMMAND)
CMD_VALIDATION: Final = ErrorCode("CMD_VALIDATION", COMMAND)
CMD_DISPATCH: Final = ErrorCode("CMD_DISPATCH", COMMAND)


class CommandError(UnoError):
    """Base class for command-related errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = CMD_ERROR,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            **kwargs,
        )


class CommandHandlerError(CommandError):
    """Error raised when a command handler encounters a problem."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = CMD_HANDLER,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message, code=code, severity=severity, context=context, **kwargs
        )


class CommandNotFoundError(CommandError):
    """Error raised when no handler is found for a command."""

    def __init__(
        self,
        command_type: str,
        code: ErrorCode = CMD_NOT_FOUND,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        message = f"No handler registered for command type {command_type}"
        super().__init__(
            message, code=code, severity=severity, context=context, **kwargs
        )


class CommandValidationError(CommandError):
    """Error raised when a command fails validation."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = CMD_VALIDATION,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message, code=code, severity=severity, context=context, **kwargs
        )


class CommandDispatchError(CommandError):
    """Error raised when there's a problem dispatching a command."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = CMD_DISPATCH,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message, code=code, severity=severity, context=context, **kwargs
        )
