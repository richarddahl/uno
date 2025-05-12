# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
API-specific error classes for the Uno framework.

This module defines errors related to API operations, including authentication,
authorization, validation, and resource handling.
"""

from __future__ import annotations

from typing import Any

from uno.errors.base import ErrorCategory, ErrorSeverity, UnoError

# =============================================================================
# API Errors
# =============================================================================


class APIError(UnoError):
    """Base class for all API-related errors."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        **context: Any,
    ) -> None:
        """Initialize an API-specific error.

        Args:
            message: Human-readable error message
            code: Error code without prefix (will be prefixed automatically)
            severity: How severe this error is
            **context: Additional context information
        """
        super().__init__(
            message=message,
            code=f"API_{code}" if code else "API_ERROR",
            category=ErrorCategory.API,
            severity=severity,
            **context,
        )


class APIAuthenticationError(APIError):
    """Raised when API authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        code: str | None = "AUTH_FAILED",
        **context: Any,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            **context,
        )


class APIAuthorizationError(APIError):
    """Raised when API authorization fails."""

    def __init__(
        self,
        message: str = "Authorization failed",
        resource: str | None = None,
        action: str | None = None,
        code: str | None = "AUTH_DENIED",
        **context: Any,
    ) -> None:
        ctx = context.copy()
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


class APIValidationError(APIError):
    """Raised when API input validation fails."""

    def __init__(
        self,
        message: str = "Validation failed",
        field: str | None = None,
        value: Any | None = None,
        code: str | None = "VALIDATION_ERROR",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if field:
            ctx["field"] = field
        if value is not None:
            ctx["value"] = str(value)

        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )


class APIResourceNotFoundError(APIError):
    """Raised when an API resource is not found."""

    def __init__(
        self,
        resource_type: str,
        resource_id: Any,
        message: str | None = None,
        code: str | None = "RESOURCE_NOT_FOUND",
        **context: Any,
    ) -> None:
        message = message or f"{resource_type} with ID '{resource_id}' not found"

        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            resource_type=resource_type,
            resource_id=str(resource_id),
            **context,
        )


class APIRateLimitError(APIError):
    """Raised when API rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        limit: int | None = None,
        reset_after: int | None = None,
        code: str | None = "RATE_LIMIT_EXCEEDED",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if limit:
            ctx["limit"] = limit
        if reset_after:
            ctx["reset_after"] = reset_after

        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )
