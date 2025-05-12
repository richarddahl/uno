# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Validation-specific error classes for the Uno framework.

This module defines errors related to validation operations, including
schema validation, input validation, and business rule validation.
"""

from typing import Any
from uno.errors.base import UnoError, ErrorCategory, ErrorSeverity


# =============================================================================
# Validation Errors
# =============================================================================


class ValidationError(UnoError):
    """Base class for all validation-related errors."""
    def __init__(
        self,
        message: str,
        code: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(
            code=f"VAL_{code}" if code else "VAL_ERROR",
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=severity,
            context=context or {},
        )


class SchemaValidationError(ValidationError):
    """Raised when schema validation fails."""
    def __init__(
        self,
        message: str,
        schema_name: str | None = None,
        field_name: str | None = None,
        field_value: Any | None = None,
        code: str | None = "SCHEMA_ERROR",
        context: dict[str, Any] | None = None,
    ):
        ctx = context.copy() if context else {}
        if schema_name:
            ctx["schema_name"] = schema_name
        if field_name:
            ctx["field_name"] = field_name
        if field_value is not None:
            ctx["field_value"] = str(field_value)
        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            context=ctx,
        )


class InputValidationError(ValidationError):
    """Raised when input validation fails."""
    def __init__(
        self,
        message: str,
        field_name: str | None = None,
        field_value: Any | None = None,
        code: str | None = "INPUT_ERROR",
        context: dict[str, Any] | None = None,
    ):
        ctx = context.copy() if context else {}
        if field_name:
            ctx["field_name"] = field_name
        if field_value is not None:
            ctx["field_value"] = str(field_value)
        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            context=ctx,
        )


class BusinessRuleValidationError(ValidationError):
    """Raised when a business rule validation fails."""
    def __init__(
        self,
        message: str,
        rule_name: str | None = None,
        code: str | None = "BUSINESS_RULE_ERROR",
        context: dict[str, Any] | None = None,
    ):
        ctx = context.copy() if context else {}
        if rule_name:
            ctx["rule_name"] = rule_name
        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            context=ctx,
        )
