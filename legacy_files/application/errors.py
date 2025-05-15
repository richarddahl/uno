# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
API-specific error classes for the Uno framework.

This module defines errors related to API operations, including authentication,
authorization, validation, and resource handling.
"""

from __future__ import annotations

from typing import Any, Final

from uno.errors.base import ErrorCode, ErrorCategory, ErrorSeverity, UnoError

# Define application-specific error categories and codes here
APPLICATION = ErrorCategory("APPLICATION")
APPLICATION_ERROR: Final = ErrorCode("APPLICATION_ERROR", APPLICATION)
APPLICATION_STARTUP: Final = ErrorCode("APPLICATION_STARTUP", APPLICATION)
APPLICATION_SHUTDOWN: Final = ErrorCode("APPLICATION_SHUTDOWN", APPLICATION)


class ApplicationError(UnoError):
    """Base class for all application-related errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = APPLICATION_ERROR,
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


class ApplicationStartupError(ApplicationError):
    """Error raised during application startup."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = APPLICATION_STARTUP,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message, code=code, severity=severity, context=context, **kwargs
        )


class ApplicationShutdownError(ApplicationError):
    """Error raised during application shutdown."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = APPLICATION_SHUTDOWN,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message, code=code, severity=severity, context=context, **kwargs
        )
