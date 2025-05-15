# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Domain-specific error classes for the Uno framework.
"""

from __future__ import annotations

from typing import Any, Final

from uno.errors.base import ErrorCode, ErrorCategory, ErrorSeverity, UnoError


# Define domain-specific error categories and codes here
DOMAIN = ErrorCategory("DOMAIN")
DOMAIN_ERROR: Final = ErrorCode("DOMAIN_ERROR", DOMAIN)
DOMAIN_VALIDATION: Final = ErrorCode("DOMAIN_VALIDATION", DOMAIN)
DOMAIN_AGGREGATE_NOT_DELETED: Final = ErrorCode("DOMAIN_AGGREGATE_NOT_DELETED", DOMAIN)


class DomainError(UnoError):
    """Base class for all domain-related errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = DOMAIN_ERROR,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a domain error.

        Args:
            message: Human-readable error message
            code: Error code
            severity: How severe this error is
            context: Additional context information
            **kwargs: Additional context keys
        """
        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            **kwargs,
        )


class DomainValidationError(DomainError):
    """Raised when domain validation fails."""

    def __init__(
        self,
        message: str = "Domain validation failed",
        field: str | None = None,
        code: ErrorCode = DOMAIN_VALIDATION,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        # Simply pass field directly as a keyword argument
        # UnoError.__init__ will handle merging it with the context
        super().__init__(
            message=message,
            code=code,
            severity=severity,
            context=context,
            field=field,
            **kwargs,
        )


class AggregateNotDeletedError(DomainError):
    """Raised when attempting to restore an aggregate that is not deleted."""

    def __init__(
        self,
        message: str = "Cannot restore an aggregate that is not deleted",
        aggregate_id: str | None = None,
        code: ErrorCode = DOMAIN_AGGREGATE_NOT_DELETED,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        # Simply pass aggregate_id directly as a keyword argument
        super().__init__(
            message=message,
            code=code,
            severity=severity,
            context=context,
            aggregate_id=aggregate_id,
            **kwargs,
        )
