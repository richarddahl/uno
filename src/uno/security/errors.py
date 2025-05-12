# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Security-specific error classes for the Uno framework.

This module defines errors related to security operations, including
authentication, authorization, and token handling.
"""

from __future__ import annotations

from typing import Any

from uno.errors.base import ErrorCategory, ErrorSeverity, UnoError

# =============================================================================
# Security Errors
# =============================================================================


class SecurityError(UnoError):
    """Base class for all security-related errors."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        **context: Any,
    ) -> None:
        """Initialize a security error.

        Args:
            message: Human-readable error message
            code: Error code without prefix (will be prefixed automatically)
            severity: How severe this error is
            **context: Additional context information
        """
        super().__init__(
            message=message,
            code=f"SEC_{code}" if code else "SEC_ERROR",
            category=ErrorCategory.SECURITY,
            severity=severity,
            **context,
        )


class AuthenticationError(SecurityError):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        username: str | None = None,
        code: str | None = "AUTH_FAILED",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if username:
            ctx["username"] = username

        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )


class AuthorizationError(SecurityError):
    """Raised when authorization fails."""

    def __init__(
        self,
        message: str = "Authorization failed",
        username: str | None = None,
        resource: str | None = None,
        action: str | None = None,
        code: str | None = "AUTH_DENIED",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if username:
            ctx["username"] = username
        if resource:
            ctx["resource"] = resource
        if action:
            ctx["action"] = action

        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )


class TokenError(SecurityError):
    """Raised when there's an issue with a security token."""

    def __init__(
        self,
        message: str,
        code: str | None = "TOKEN_ERROR",
        **context: Any,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            **context,
        )


class TokenExpiredError(TokenError):
    """Raised when a security token has expired."""

    def __init__(
        self,
        message: str = "Token has expired",
        expiry_time: str | None = None,
        code: str | None = "TOKEN_EXPIRED",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if expiry_time:
            ctx["expiry_time"] = expiry_time

        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )


class TokenInvalidError(TokenError):
    """Raised when a security token is invalid."""

    def __init__(
        self,
        message: str = "Token is invalid",
        reason: str | None = None,
        code: str | None = "TOKEN_INVALID",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if reason:
            ctx["reason"] = reason

        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )
