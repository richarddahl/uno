# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Base error classes and utilities for the Uno error handling framework.

This module provides the foundation for structured error handling with
error codes, contextual information, and error categories.
"""

import contextvars
import functools
import inspect
import traceback
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

# Type for error context dict
ErrorContext = dict[str, Any]

# Thread-local storage for error context
_error_context = contextvars.ContextVar[ErrorContext]("error_context", default={})


def get_error_context() -> ErrorContext:
    """
    Get the current error context.

    Returns:
        The current error context dictionary
    """
    return _error_context.get().copy()


def add_error_context(**context: Any) -> None:
    """
    Add key-value pairs to the current error context.

    Args:
        **context: Key-value pairs to add to the context
    """
    current = _error_context.get().copy()
    current.update(context)
    _error_context.set(current)


class _ErrorContextManager:
    """Context manager for error context."""

    def __init__(self, **context_kwargs: Any):
        """Initialize with context key-value pairs."""
        self.context_kwargs = context_kwargs
        self.token = None

    def __enter__(self):
        """Enter the error context, updating the current context."""
        current_context = _error_context.get().copy()
        new_context = current_context.copy()
        new_context.update(self.context_kwargs)
        self.token = _error_context.set(new_context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the error context, restoring the previous context."""
        if self.token is not None:
            _error_context.reset(self.token)


def with_error_context(*args, **kwargs) -> Any:
    """
    Decorator or context manager for adding context to errors.

    Can be used as:
    1. Decorator: @with_error_context
    2. Context manager: with with_error_context(key=value):

    Args:
        *args: Function to decorate (if used as decorator)
        **kwargs: Key-value pairs to add to the context (if used as context manager)

    Returns:
        Decorated function or context manager
    """
    # If used as a decorator (no kwargs and one positional arg which is callable)
    if kwargs == {} and len(args) == 1 and callable(args[0]):
        func = args[0]

        @functools.wraps(func)
        def wrapper(*f_args: Any, **f_kwargs: Any) -> Any:
            # Get the signature of the function
            sig = inspect.signature(func)

            # Bind the arguments to the signature
            bound = sig.bind(*f_args, **f_kwargs)
            bound.apply_defaults()

            # Use the context manager
            with _ErrorContextManager(**bound.arguments):
                return func(*f_args, **f_kwargs)

        return wrapper

    # If used as a context manager
    return _ErrorContextManager(**kwargs)


class _AsyncErrorContextManager:
    """Async context manager for error context."""

    def __init__(self, **context_kwargs: Any):
        """Initialize with context key-value pairs."""
        self.context_kwargs = context_kwargs
        self.token = None

    async def __aenter__(self):
        """Enter the error context, updating the current context."""
        current_context = _error_context.get().copy()
        new_context = current_context.copy()
        new_context.update(self.context_kwargs)
        self.token = _error_context.set(new_context)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the error context, restoring the previous context."""
        if self.token is not None:
            _error_context.reset(self.token)


def with_async_error_context(*args, **kwargs) -> Any:
    """
    Decorator or async context manager for adding context to errors.

    Can be used as:
    1. Decorator: @with_async_error_context
    2. Async context manager: async with with_async_error_context(key=value):

    Args:
        *args: Function to decorate (if used as decorator)
        **kwargs: Key-value pairs to add to the context (if used as context manager)

    Returns:
        Decorated async function or async context manager
    """
    # If used as a decorator (no kwargs and one positional arg which is callable)
    if kwargs == {} and len(args) == 1 and callable(args[0]):
        func = args[0]

        @functools.wraps(func)
        async def wrapper(*f_args: Any, **f_kwargs: Any) -> Any:
            # Get the signature of the function
            sig = inspect.signature(func)

            # Bind the arguments to the signature
            bound = sig.bind(*f_args, **f_kwargs)
            bound.apply_defaults()

            # Use the async context manager
            async with _AsyncErrorContextManager(**bound.arguments):
                return await func(*f_args, **f_kwargs)

        return wrapper

    # If used as an async context manager
    return _AsyncErrorContextManager(**kwargs)


class ErrorCategory(Enum):
    """
    Categories of errors for classification.

    These categories help classify errors for appropriate handling
    and reporting.
    """

    # General categories
    VALIDATION = auto()  # Input validation errors
    BUSINESS_RULE = auto()  # Business rule violations
    AUTHORIZATION = auto()  # Permission/authorization errors
    AUTHENTICATION = auto()  # Login/identity errors
    SECURITY = auto()  # Security-related errors

    # Resource-related categories
    RESOURCE = auto()  # Resource availability errors
    NOT_FOUND = auto()  # Resource not found
    CONFLICT = auto()  # Resource conflicts

    # System-related categories
    DATABASE = auto()  # Database-related errors
    NETWORK = auto()  # Network/connectivity errors
    CONFIGURATION = auto()  # System configuration errors
    DEPENDENCY = auto()  # Dependency resolution errors
    SYSTEM = auto()  # System-level errors
    APPLICATION = auto()  # Application-level errors

    # Processing-related categories
    EXECUTION = auto()  # Execution/processing errors
    INITIALIZATION = auto()  # Initialization errors
    SERIALIZATION = auto()  # Serialization/deserialization errors
    FILTER = auto()  # Filtering errors

    # Miscellaneous categories
    INTEGRATION = auto()  # External system integration errors
    INTERNAL = auto()  # Unexpected internal errors
    UNEXPECTED = auto()  # Unexpected errors


class ErrorSeverity(Enum):
    """
    Severity levels for errors.

    These severity levels help prioritize error handling and reporting.
    """

    INFO = auto()  # Informational message, not an error
    WARNING = auto()  # Warning that might need attention
    ERROR = auto()  # Error that affects operation but not critical
    CRITICAL = auto()  # Critical error that prevents core functionality
    FATAL = auto()  # Fatal error that requires system shutdown


@dataclass(frozen=True)
class ErrorInfo:
    """
    Information about an error code.

    This class stores metadata about error codes for documentation
    and consistent handling.
    """

    code: str
    message_template: str
    category: ErrorCategory
    severity: ErrorSeverity
    description: str
    http_status_code: int | None = None
    retry_allowed: bool = True


class ErrorCode:
    """
    Error code constants and utilities.

    This class provides standardized error codes and utilities
    for working with them.
    """

    # Core error codes
    UNKNOWN_ERROR = "CORE-0001"
    VALIDATION_ERROR = "CORE-0002"
    AUTHORIZATION_ERROR = "CORE-0003"
    AUTHENTICATION_ERROR = "CORE-0004"
    RESOURCE_NOT_FOUND = "CORE-0005"
    RESOURCE_CONFLICT = "CORE-0006"
    INTERNAL_ERROR = "CORE-0007"
    CONFIGURATION_ERROR = "CORE-0008"
    DEPENDENCY_ERROR = "CORE-0009"
    TIMEOUT_ERROR = "CORE-0010"

    # Database error codes
    DB_CONNECTION_ERROR = "DB-0001"
    DB_QUERY_ERROR = "DB-0002"
    DB_INTEGRITY_ERROR = "DB-0003"
    DB_TRANSACTION_ERROR = "DB-0004"
    DB_DEADLOCK_ERROR = "DB-0005"

    # API error codes
    API_REQUEST_ERROR = "API-0001"
    API_RESPONSE_ERROR = "API-0002"
    API_RATE_LIMIT_ERROR = "API-0003"
    API_INTEGRATION_ERROR = "API-0004"

    @staticmethod
    def is_valid(code: str) -> bool:
        """
        Check if an error code is valid.

        Args:
            code: The error code to check

        Returns:
            True if the code is valid, False otherwise
        """
        from uno.core.errors.catalog import get_error_code_info

        return get_error_code_info(code) is not None

    @staticmethod
    def get_http_status(code: str) -> int:
        """
        Get the HTTP status code for an error code.

        Args:
            code: The error code

        Returns:
            The HTTP status code (defaults to 500 if not specified)
        """
        from uno.core.errors.catalog import get_error_code_info

        info = get_error_code_info(code)
        return info.http_status_code if info and info.http_status_code else 500


class FrameworkError(Exception):
    """
    Base class for all Uno framework errors.

    This class provides standardized error formatting with error codes,
    contextual information, and stacktrace capture.
    """

    def __init__(self, message: str, error_code: str, **context: Any):
        super().__init__(message)
        self.message: str = message
        self.error_code: str = error_code
        self.context: dict[str, Any] = get_error_context().copy()
        self.context.update(context)
        self.traceback: str = "".join(traceback.format_exception(*traceback.sys.exc_info()))
        from uno.core.errors.catalog import get_error_code_info
        self.error_info: ErrorInfo | None = get_error_code_info(error_code)

    @property
    def category(self) -> ErrorCategory | None:
        return self.error_info.category if self.error_info else None

    @property
    def severity(self) -> ErrorSeverity | None:
        return self.error_info.severity if self.error_info else None

    @property
    def http_status_code(self) -> int | None:
        if self.error_info and self.error_info.http_status_code:
            return self.error_info.http_status_code
        return 500

    @property
    def retry_allowed(self) -> bool:
        if self.error_info:
            return self.error_info.retry_allowed
        return True

    def to_dict(self) -> dict[str, Any]:
        result = {
            "message": self.message,
            "error_code": self.error_code,
            "context": self.context,
        }
        if self.category:
            result["category"] = self.category.name
        if self.severity:
            result["severity"] = self.severity.name
        return result

    def __str__(self) -> str:
        return f"{self.error_code}: {self.message}"



    """Error raised when domain validation fails."""

    def __init__(self, message: str, entity_name: str | None = None, **context: Any):
        """
        Initialize a DomainValidationError.

        Args:
            message: The error message
            entity_name: The name of the entity that failed validation
            **context: Additional context information
        """
        context_dict = context.copy()
        if entity_name:
            context_dict["entity_name"] = entity_name

        super().__init__(
            message=message, error_code=ErrorCode.VALIDATION_ERROR, **context_dict
        )



    """Error raised when an aggregate invariant is violated."""

    def __init__(
        self,
        message: str,
        aggregate_name: str | None = None,
        aggregate_id: str | None = None,
        **context: Any,
    ):
        """
        Initialize an AggregateInvariantViolationError.

        Args:
            message: The error message
            aggregate_name: The name of the aggregate
            aggregate_id: The ID of the aggregate
            **context: Additional context information
        """
        context_dict = context.copy()
        if aggregate_name:
            context_dict["aggregate_name"] = aggregate_name
        if aggregate_id:
            context_dict["aggregate_id"] = aggregate_id

        super().__init__(
            message=message, error_code=ErrorCode.BUSINESS_RULE, **context_dict
        )



    """Error raised when an entity is not found."""

    def __init__(self, entity_type: str, entity_id: Any, **context: Any):
        """
        Initialize an EntityNotFoundError.

        Args:
            entity_type: The type of entity that was not found
            entity_id: The ID of the entity that was not found
            **context: Additional context information
        """
        message = f"{entity_type} with ID {entity_id} not found"
        super().__init__(
            message=message,
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            entity_type=entity_type,
            entity_id=entity_id,
            **context,
        )



    """Error raised when there is a concurrency conflict."""

    def __init__(
        self,
        entity_type: str,
        entity_id: Any,
        expected_version: int | None = None,
        actual_version: int | None = None,
        **context: Any,
    ):
        """
        Initialize a ConcurrencyError.

        Args:
            entity_type: The type of entity with the concurrency conflict
            entity_id: The ID of the entity with the concurrency conflict
            expected_version: The expected version of the entity
            actual_version: The actual version of the entity
            **context: Additional context information
        """
        message = f"Concurrency conflict detected for {entity_type} with ID {entity_id}"

        context_dict = context.copy()
        if expected_version is not None:
            context_dict["expected_version"] = expected_version
        if actual_version is not None:
            context_dict["actual_version"] = actual_version

        super().__init__(
            message=message,
            error_code=ErrorCode.RESOURCE_CONFLICT,
            entity_type=entity_type,
            entity_id=entity_id,
            **context_dict,
        )



    """Error raised when user is not authorized to perform an operation."""

    def __init__(
        self,
        message: str = "User is not authorized to perform this operation",
        resource_type: str | None = None,
        resource_id: Any | None = None,
        permission: str | None = None,
        **context: Any,
    ):
        """
        Initialize an AuthorizationError.

        Args:
            message: The error message
            resource_type: The type of resource the user tried to access
            resource_id: The ID of the resource the user tried to access
            permission: The permission the user was missing
            **context: Additional context information
        """
        context_dict = context.copy()
        if resource_type:
            context_dict["resource_type"] = resource_type
        if resource_id:
            context_dict["resource_id"] = resource_id
        if permission:
            context_dict["permission"] = permission

        super().__init__(
            message=message, error_code=ErrorCode.AUTHORIZATION_ERROR, **context_dict
        )



    """Error raised when validation fails."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any | None = None,
        **context: Any,
    ):
        """
        Initialize a ValidationError.

        Args:
            message: The error message
            field: The field that failed validation
            value: The value that failed validation
            **context: Additional context information
        """
        context_dict = context.copy()
        if field:
            context_dict["field"] = field
        if value is not None:
            context_dict["value"] = value

        super().__init__(
            message=message, error_code=ErrorCode.VALIDATION_ERROR, **context_dict
        )
