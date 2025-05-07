"""
Domain-specific error classes for the Uno framework.

This module contains error classes that represent business rule violations
and other domain-level exceptions.
"""

from .domain_errors import (
    AggregateDeletedError,
    AggregateInvariantViolationError,
    AggregateNotDeletedError,
    BusinessRuleViolationError,
    CommandExecutionError,
    CommandHandlerNotFoundError,
    ConcurrencyError,
    DomainError,
    DomainValidationError,
    EntityNotFoundError,
    QueryExecutionError,
    QueryHandlerNotFoundError,
)

__all__ = [
    "AggregateDeletedError",
    "AggregateInvariantViolationError",
    "AggregateNotDeletedError",
    "BusinessRuleViolationError",
    "CommandExecutionError",
    "CommandHandlerNotFoundError",
    "ConcurrencyError",
    "DomainError",
    "DomainValidationError",
    "EntityNotFoundError",
    "QueryExecutionError",
    "QueryHandlerNotFoundError",
]
