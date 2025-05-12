from uno.errors.base import UnoError, ErrorCategory, ErrorSeverity
from uno.errors.codes import ErrorCode
from pydantic import BaseModel
from typing import Any


class ErrorContextModel(BaseModel):
    """Base model for error context. Extend in each factory for specific context validation."""

    pass


class BaseErrorFactory:
    @staticmethod
    def make_error(
        message: str,
        code: str,
        category: ErrorCategory = ErrorCategory.GENERIC,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
    ) -> UnoError:
        return UnoError(
            code=code,
            message=message,
            category=category,
            severity=severity,
            context=context or {},
        )
