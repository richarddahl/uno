"""
Domain-specific error classes for the Uno framework.

This module contains error classes that represent business rule violations
and other domain-level exceptions.
"""

from typing import Any, Dict
from uno.core.errors.base import FrameworkError

class DomainError(FrameworkError):
    """Base class for all domain-level exceptions."""

class DomainValidationError(FrameworkError):
    """Exception raised when domain validation fails."""

class EntityNotFoundError(FrameworkError):
    """Exception raised when an entity cannot be found."""

class BusinessRuleViolationError(FrameworkError):
    """Exception raised when a business rule is violated."""

class ConcurrencyError(FrameworkError):
    """Exception raised when a concurrency conflict occurs."""

class AggregateInvariantViolationError(FrameworkError):
    """Exception raised when an aggregate invariant is violated."""

class AggregateDeletedError(FrameworkError):
    """Raised when attempting to mutate a deleted aggregate."""

class AggregateNotDeletedError(FrameworkError):
    """Raised when attempting to restore an aggregate that is not deleted."""

class CommandHandlerNotFoundError(FrameworkError):
    """Exception raised when a command handler cannot be found."""

class CommandExecutionError(FrameworkError):
    """Exception raised when a command execution fails."""

class QueryHandlerNotFoundError(FrameworkError):
    """Exception raised when a query handler cannot be found."""

class QueryExecutionError(FrameworkError):
    """Exception raised when a query execution fails."""
