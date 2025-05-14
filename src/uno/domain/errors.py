# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Domain-specific error classes for the Uno framework.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel
from uno.errors.base import ErrorSeverity


class ErrorCategory(str, Enum):
    """Categories for domain errors."""

    DOMAIN = "domain"
    VALIDATION = "validation"


# =============================================================================
# Domain Errors
# =============================================================================


class DomainErrorContext(BaseModel):
    """Context model for domain errors."""

    code: str
    category: ErrorCategory = ErrorCategory.DOMAIN
    severity: ErrorSeverity = ErrorSeverity.ERROR
    context: dict[str, Any] = {}


class DomainError(Exception):
    """Base class for all domain-related errors (Uno idiom: local, Pydantic context)."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        **context: Any,
    ) -> None:
        """Initialize a domain error.

        Args:
            message: Human-readable error message
            code: Error code without prefix (will be prefixed automatically)
            severity: How severe this error is
            **context: Additional context information
        """
        self.message = message
        self.context = DomainErrorContext(
            code=f"DOM_{code}" if code else "DOM_ERROR",
            severity=severity,
            context=context,
        )
        super().__init__(message)


class DomainValidationError(DomainError):
    """Raised when domain validation fails."""

    def __init__(
        self,
        message: str = "Domain validation failed",
        field: str | None = None,
        code: str | None = "VALIDATION_FAILED",
        **context: Any,
    ) -> None:
        ctx = {}
        if field:
            ctx["field"] = field
        ctx.update(context)

        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )


class AggregateNotDeletedError(DomainError):
    """Raised when attempting to restore an aggregate that is not deleted."""

    def __init__(
        self,
        message: str = "Cannot restore an aggregate that is not deleted",
        aggregate_id: str | None = None,
        code: str | None = "AGGREGATE_NOT_DELETED",
        **context: Any,
    ) -> None:
        ctx = {}
        if aggregate_id:
            ctx["aggregate_id"] = aggregate_id
        ctx.update(context)

        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )
