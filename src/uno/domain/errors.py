# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT

"""
Domain error definitions.
"""

from typing import Any

from uno.errors.base import UnoError

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


"""
Domain error definitions for Uno.

This module defines all business rule and validation errors for the domain layer.
All errors inherit from UnoError and use DomainErrorCode values for error_code.
"""

from typing import Any
from uno.errors.base import UnoError


class DomainValidationError(UnoError):
    """Raised when domain validation fails."""

    def __init__(
        self, message: str, details: dict[str, Any] | None = None, **context: Any
    ):
        super().__init__(
            message=message,
            error_code=DomainErrorCode.VALIDATION_ERROR,
            details=details or {},
            **context,
        )


class EntityNotFoundError(UnoError):
    """Raised when an entity is not found."""

    def __init__(self, entity_type: str, entity_id: Any, **context: Any):
        super().__init__(
            message=f"Entity of type '{entity_type}' with id '{entity_id}' not found.",
            error_code=DomainErrorCode.ENTITY_NOT_FOUND,
            details={"entity_type": entity_type, "entity_id": entity_id},
            **context,
        )


class BusinessRuleViolationError(UnoError):
    """Raised when a business rule is violated."""

    def __init__(
        self,
        message: str,
        rule_name: str,
        details: dict[str, Any] | None = None,
        **context: Any,
    ):
        super().__init__(
            message=message,
            error_code=DomainErrorCode.BUSINESS_RULE_VIOLATION,
            details={"rule_name": rule_name, **(details or {})},
            **context,
        )


class ConcurrencyError(UnoError):
    """Raised when a concurrency conflict occurs."""

    def __init__(self, entity_type: str, entity_id: Any, **context: Any):
        super().__init__(
            message=f"Concurrency conflict for entity '{entity_type}' with id '{entity_id}'.",
            error_code=DomainErrorCode.CONCURRENCY_ERROR,
            details={"entity_type": entity_type, "entity_id": entity_id},
            **context,
        )


class AggregateInvariantViolationError(UnoError):
    """Raised when an aggregate invariant is violated."""

    def __init__(
        self, aggregate_type: str, invariant_name: str, message: str, **context: Any
    ):
        super().__init__(
            message=message,
            error_code=DomainErrorCode.AGGREGATE_INVARIANT_VIOLATION,
            details={
                "aggregate_type": aggregate_type,
                "invariant_name": invariant_name,
            },
            **context,
        )


class CommandHandlerNotFoundError(UnoError):
    """Raised when a command handler is not found."""

    def __init__(self, command_type: str, **context: Any):
        super().__init__(
            message=f"No handler registered for command '{command_type}'.",
            error_code=DomainErrorCode.COMMAND_HANDLER_NOT_FOUND,
            details={"command_type": command_type},
            **context,
        )


class QueryHandlerNotFoundError(UnoError):
    """Raised when a query handler is not found."""

    def __init__(self, query_type: str, **context: Any):
        super().__init__(
            message=f"No handler registered for query '{query_type}'.",
            error_code=DomainErrorCode.QUERY_HANDLER_NOT_FOUND,
            details={"query_type": query_type},
            **context,
        )


class CommandExecutionError(UnoError):
    """Raised when a command execution fails."""

    def __init__(
        self,
        command_type: str,
        message: str,
        details: dict[str, Any] | None = None,
        **context: Any,
    ):
        super().__init__(
            message=message,
            error_code=DomainErrorCode.COMMAND_EXECUTION_ERROR,
            details={"command_type": command_type, **(details or {})},
            **context,
        )


class QueryExecutionError(UnoError):
    """Raised when a query execution fails."""

    def __init__(
        self,
        query_type: str,
        message: str,
        details: dict[str, Any] | None = None,
        **context: Any,
    ):
        super().__init__(
            message=message,
            error_code=DomainErrorCode.QUERY_EXECUTION_ERROR,
            details={"query_type": query_type, **(details or {})},
            **context,
        )


class DomainAuthorizationError(UnoError):
    """Raised when domain authorization fails."""

    def __init__(
        self, message: str, details: dict[str, Any] | None = None, **context: Any
    ):
        super().__init__(
            message=message,
            error_code=DomainErrorCode.AUTHORIZATION_ERROR,
            details=details or {},
            **context,
        )


class DomainValidationError(UnoError):
    """Raised when domain validation fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            code=DomainErrorCode.VALIDATION_ERROR,
            details=details,
        )


class EntityNotFoundError(UnoError):
    """Raised when an entity is not found."""

    def __init__(self, entity_type: str, entity_id: Any):
        super().__init__(
            message=f"Entity of type '{entity_type}' with id '{entity_id}' not found.",
            code=DomainErrorCode.ENTITY_NOT_FOUND,
            details={"entity_type": entity_type, "entity_id": entity_id},
        )


class BusinessRuleViolationError(UnoError):
    """Raised when a business rule is violated."""

    def __init__(
        self, message: str, rule_name: str, details: dict[str, Any] | None = None
    ):
        super().__init__(
            message=message,
            code=DomainErrorCode.BUSINESS_RULE_VIOLATION,
            details={"rule_name": rule_name, **(details or {})},
        )


class ConcurrencyError(UnoError):
    """Raised when a concurrency conflict occurs."""

    def __init__(self, entity_type: str, entity_id: Any):
        super().__init__(
            message=f"Concurrency conflict for entity '{entity_type}' with id '{entity_id}'.",
            code=DomainErrorCode.CONCURRENCY_ERROR,
            details={"entity_type": entity_type, "entity_id": entity_id},
        )


class AggregateInvariantViolationError(UnoError):
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


class CommandHandlerNotFoundError(UnoError):
    """Raised when a command handler is not found."""

    def __init__(self, command_type: str):
        super().__init__(
            message=f"No handler registered for command '{command_type}'.",
            code=DomainErrorCode.COMMAND_HANDLER_NOT_FOUND,
            details={"command_type": command_type},
        )


class QueryHandlerNotFoundError(UnoError):
    """Raised when a query handler is not found."""

    def __init__(self, query_type: str):
        super().__init__(
            message=f"No handler registered for query '{query_type}'.",
            code=DomainErrorCode.QUERY_HANDLER_NOT_FOUND,
            details={"query_type": query_type},
        )


class CommandExecutionError(UnoError):
    """Raised when a command execution fails."""

    def __init__(
        self, command_type: str, message: str, details: dict[str, Any] | None = None
    ):
        super().__init__(
            message=message,
            code=DomainErrorCode.COMMAND_EXECUTION_ERROR,
            details={"command_type": command_type, **(details or {})},
        )


class QueryExecutionError(UnoError):
    """Raised when a query execution fails."""

    def __init__(
        self, query_type: str, message: str, details: dict[str, Any] | None = None
    ):
        super().__init__(
            message=message,
            code=DomainErrorCode.QUERY_EXECUTION_ERROR,
            details={"query_type": query_type, **(details or {})},
        )


class DomainAuthorizationError(UnoError):
    """Raised when domain authorization fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            code=DomainErrorCode.AUTHORIZATION_ERROR,
            details=details,
        )


class AggregateNotDeletedError(UnoError):
    """Raised when an aggregate cannot be deleted."""

    def __init__(self, message: str, **context: Any):
        super().__init__(message=message, error_code="CORE-0011", **context)
