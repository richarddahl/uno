# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT

"""
Logging error definitions.
"""

from typing import Any

from uno.core.errors.base import FrameworkError

# -----------------------------------------------------------------------------
# Logging error codes
# -----------------------------------------------------------------------------


class LoggingErrorCode:
    """Error codes for logging system."""

    CONFIG_ERROR = "LOG-1001"
    HANDLER_ERROR = "LOG-1002"
    FORMAT_ERROR = "LOG-1003"
    WRITE_ERROR = "LOG-1004"
    ROTATION_ERROR = "LOG-1005"
    FILTER_ERROR = "LOG-1006"


# -----------------------------------------------------------------------------
# Logging error classes
# -----------------------------------------------------------------------------


class LoggingConfigError(FrameworkError):
    """Raised when logging configuration is invalid."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=LoggingErrorCode.CONFIG_ERROR,
            **context,
        )


class LoggingHandlerError(FrameworkError):
    """Raised when a logging handler fails."""

    def __init__(self, handler_name: str, reason: str, **context: Any):
        super().__init__(
            message=f"Handler '{handler_name}' failed: {reason}",
            error_code=LoggingErrorCode.HANDLER_ERROR,
            handler_name=handler_name,
            reason=reason,
            **context,
        )


class LoggingFormatError(FrameworkError):
    """Raised when log message formatting fails."""

    def __init__(self, message: str, **context: Any):
        super().__init__(
            message=message,
            error_code=LoggingErrorCode.FORMAT_ERROR,
            **context,
        )


class LoggingWriteError(FrameworkError):
    """Raised when writing to a log fails."""

    def __init__(self, target: str, reason: str, **context: Any):
        super().__init__(
            message=f"Failed to write to log '{target}': {reason}",
            error_code=LoggingErrorCode.WRITE_ERROR,
            target=target,
            reason=reason,
            **context,
        )


class LoggingRotationError(FrameworkError):
    """Raised when log rotation fails."""

    def __init__(self, log_file: str, reason: str, **context: Any):
        super().__init__(
            message=f"Failed to rotate log file '{log_file}': {reason}",
            error_code=LoggingErrorCode.ROTATION_ERROR,
            log_file=log_file,
            reason=reason,
            **context,
        )


class LoggingFilterError(FrameworkError):
    """Raised when a logging filter fails."""

    def __init__(self, filter_name: str, reason: str, **context: Any):
        super().__init__(
            message=f"Filter '{filter_name}' failed: {reason}",
            error_code=LoggingErrorCode.FILTER_ERROR,
            filter_name=filter_name,
            reason=reason,
            **context,
        ) 