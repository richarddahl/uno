# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT

"""
Domain error definitions.
"""

from typing import Any

from uno.core.errors.base import FrameworkError

# -----------------------------------------------------------------------------
# Domain error codes
# -----------------------------------------------------------------------------


class DomainErrorCode:
    """Error codes for domain layer."""

    VALIDATION_ERROR = "DOMAIN-1001"
    ENTITY_NOT_FOUND = "DOMAIN-1002"
    BUSINESS_RULE_VIOLATION = "DOMAIN-1003"
    CONCURRENCY_ERROR = "DOMAIN-1004"
    AGGREGATE_INVARIANT_VIOLATION = "DOMAIN-1005"
    COMMAND_HANDLER_NOT_FOUND = "DOMAIN-1006"
    QUERY_HANDLER_NOT_FOUND = "DOMAIN-1007"
    COMMAND_EXECUTION_ERROR = "DOMAIN-1008"
    QUERY_EXECUTION_ERROR = "DOMAIN-1009"
    AUTHORIZATION_ERROR = "DOMAIN-1010"


# -----------------------------------------------------------------------------
# Domain error classes
# -----------------------------------------------------------------------------


class DomainError(FrameworkError):
    """Base class for domain errors."""

    def __init__(
        self, message: str, code: str, details: dict[str, Any] | None = None, **kwargs
    ):
        super().__init__(
            message=message,
            error_code=code,
            details=details or {},
            **kwargs,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary."""
        result = {
            "message": self.message,
            "code": self.error_code,
            "details": self.details,
        }
        return result


class DomainValidationError(DomainError):
    """Raised when domain validation fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            code=DomainErrorCode.VALIDATION_ERROR,
            details=details,
        )


class EntityNotFoundError(DomainError):
    """Raised when an entity is not found."""

    def __init__(self, entity_type: str, entity_id: Any):
        super().__init__(
            message=f"Entity of type '{entity_type}' with id '{entity_id}' not found.",
            code=DomainErrorCode.ENTITY_NOT_FOUND,
            details={"entity_type": entity_type, "entity_id": entity_id},
        )


class BusinessRuleViolationError(DomainError):
    """Raised when a business rule is violated."""

    def __init__(
        self, message: str, rule_name: str, details: dict[str, Any] | None = None
    ):
        super().__init__(
            message=message,
            code=DomainErrorCode.BUSINESS_RULE_VIOLATION,
            details={"rule_name": rule_name, **(details or {})},
        )


class ConcurrencyError(DomainError):
    """Raised when a concurrency conflict occurs."""

    def __init__(self, entity_type: str, entity_id: Any):
        super().__init__(
            message=f"Concurrency conflict for entity '{entity_type}' with id '{entity_id}'.",
            code=DomainErrorCode.CONCURRENCY_ERROR,
            details={"entity_type": entity_type, "entity_id": entity_id},
        )


class AggregateInvariantViolationError(DomainError):
    """Raised when an aggregate invariant is violated."""

    def __init__(self, aggregate_type: str, invariant_name: str, message: str):
        super().__init__(
            message=message,
            code=DomainErrorCode.AGGREGATE_INVARIANT_VIOLATION,
            details={
                "aggregate_type": aggregate_type,
                "invariant_name": invariant_name,
            },
        )


class CommandHandlerNotFoundError(DomainError):
    """Raised when a command handler is not found."""

    def __init__(self, command_type: str):
        super().__init__(
            message=f"No handler registered for command '{command_type}'.",
            code=DomainErrorCode.COMMAND_HANDLER_NOT_FOUND,
            details={"command_type": command_type},
        )


class QueryHandlerNotFoundError(DomainError):
    """Raised when a query handler is not found."""

    def __init__(self, query_type: str):
        super().__init__(
            message=f"No handler registered for query '{query_type}'.",
            code=DomainErrorCode.QUERY_HANDLER_NOT_FOUND,
            details={"query_type": query_type},
        )


class CommandExecutionError(DomainError):
    """Raised when a command execution fails."""

    def __init__(
        self, command_type: str, message: str, details: dict[str, Any] | None = None
    ):
        super().__init__(
            message=message,
            code=DomainErrorCode.COMMAND_EXECUTION_ERROR,
            details={"command_type": command_type, **(details or {})},
        )


class QueryExecutionError(DomainError):
    """Raised when a query execution fails."""

    def __init__(
        self, query_type: str, message: str, details: dict[str, Any] | None = None
    ):
        super().__init__(
            message=message,
            code=DomainErrorCode.QUERY_EXECUTION_ERROR,
            details={"query_type": query_type, **(details or {})},
        )


class DomainAuthorizationError(DomainError):
    """Raised when domain authorization fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            code=DomainErrorCode.AUTHORIZATION_ERROR,
            details=details,
        ) 