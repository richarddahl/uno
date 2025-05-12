# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Advanced external exception wrapping utilities for the Uno framework.

This module provides specialized utilities for wrapping external exceptions
from various libraries and frameworks with Uno error types, ensuring proper
context capturing, categorization, and error code mapping.
"""

from __future__ import annotations

import importlib.util
import inspect
import re
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar, cast

from uno.errors.base import ErrorCategory, ErrorSeverity, UnoError
from uno.errors.component_errors import (
    APIError,
    DBConnectionError,
    DBError,
    DBQueryError,
    EventError,
    SecurityError,
    ValidationError,
)

T = TypeVar("T", bound=UnoError)


@dataclass
class ExceptionMapping:
    """Mapping configuration for external exception types to Uno error types."""

    exception_type: type[Exception]
    target_error_type: type[UnoError]
    category: ErrorCategory = ErrorCategory.INTERNAL
    severity: ErrorSeverity = ErrorSeverity.ERROR
    context_extractor: Callable[[Exception], dict[str, Any]] | None = None
    message_formatter: Callable[[Exception], str] | None = None
    code_extractor: Callable[[Exception], str | None] | None = None


# Default message formatter that extracts useful details from the exception
def default_message_formatter(exception: Exception) -> str:
    """Format a default message from an exception.

    Args:
        exception: The exception to format

    Returns:
        A formatted message string
    """
    return f"{type(exception).__name__}: {exception!s}"


# Default context extractor that gets useful attributes from the exception
def default_context_extractor(exception: Exception) -> dict[str, Any]:
    """Extract context information from an exception.

    Args:
        exception: The exception to extract context from

    Returns:
        A dictionary of context information
    """
    context = {}

    # Get all public attributes that aren't methods or internal attributes
    for attr in dir(exception):
        if not attr.startswith("_") and not callable(getattr(exception, attr, None)):
            try:
                value = getattr(exception, attr)
                # Only include serializable values
                if (
                    isinstance(value, str | int | float | bool | list | dict | tuple)
                    or value is None
                ):
                    context[attr] = value
            except (Exception, AttributeError):
                # Skip attributes that can't be accessed
                pass

    # Add the exception type
    context["exception_type"] = type(exception).__name__

    # Add the module
    context["exception_module"] = type(exception).__module__

    return context


def wrap_exception(
    exception: Exception,
    message: str | None = None,
    code: str | None = None,
    category: ErrorCategory | None = None,
    severity: ErrorSeverity | None = None,
    error_class: type[UnoError] | None = None,
    mappings: list[ExceptionMapping] | None = None,
    extract_context: bool = True,
    **context: Any,
) -> UnoError:
    """Wrap an external exception in a UnoError with enhanced context.

    Args:
        exception: The exception to wrap
        message: Optional message override
        code: Error code for the wrapped exception
        category: Error category
        severity: Error severity
        error_class: Specific error class to instantiate
        mappings: Optional list of exception mappings to use
        extract_context: Whether to extract context from the exception
        **context: Additional context information

    Returns:
        A new UnoError instance with the exception as its cause
    """
    # First try to find a mapping for this exception type
    mapping = _find_matching_mapping(exception, mappings or _get_default_mappings())

    # Prepare the error information
    target_error_class = error_class or (
        mapping.target_error_type if mapping else UnoError
    )
    category = category or (mapping.category if mapping else ErrorCategory.INTERNAL)
    severity = severity or (mapping.severity if mapping else ErrorSeverity.ERROR)

    # Extract context if requested
    extracted_context = {}
    if extract_context:
        # Use mapping-specific extractor if available
        if mapping and mapping.context_extractor:
            extracted_context = mapping.context_extractor(exception)
        else:
            extracted_context = default_context_extractor(exception)

    # Format the message
    if message is None:
        if mapping and mapping.message_formatter:
            message = mapping.message_formatter(exception)
        else:
            message = default_message_formatter(exception)

    # Determine the error code
    final_code = code
    if final_code is None and mapping and mapping.code_extractor:
        final_code = mapping.code_extractor(exception)

    # Combine contexts
    combined_context = {**extracted_context, **context}

    # Ensure original_exception is set for backwards compatibility
    if (
        "exception_type" in combined_context
        and "original_exception" not in combined_context
    ):
        combined_context["original_exception"] = combined_context["exception_type"]

    # Create the error
    error = target_error_class(
        message=message,
        code=final_code,
        category=category,
        severity=severity,
        **combined_context,
    )

    # Set the cause
    error.__cause__ = exception

    # Add stack trace information if available
    if hasattr(exception, "__traceback__") and exception.__traceback__:
        error.traceback_str = "".join(traceback.format_tb(exception.__traceback__))

    return error


def _find_matching_mapping(
    exception: Exception, mappings: list[ExceptionMapping]
) -> ExceptionMapping:
    """Find the first mapping that matches the given exception.

    Args:
        exception: The exception to match
        mappings: List of exception mappings to check

    Returns:
        The matching mapping or None if no match is found
    """
    exception_type = type(exception)

    # First try direct type match
    for mapping in mappings:
        if exception_type is mapping.exception_type:
            return mapping

    # Then try inheritance
    for mapping in mappings:
        if isinstance(exception, mapping.exception_type):
            return mapping

    return None


def _get_default_mappings() -> list[ExceptionMapping]:
    """Get default mappings for common external exceptions.

    Returns:
        A list of default exception mappings
    """
    mappings = []

    # Add SQLAlchemy mappings if available
    sqlalchemy_mappings = _get_sqlalchemy_mappings()
    if sqlalchemy_mappings:
        mappings.extend(sqlalchemy_mappings)

    # Add Pydantic mappings if available
    pydantic_mappings = _get_pydantic_mappings()
    if pydantic_mappings:
        mappings.extend(pydantic_mappings)

    # Add requests mappings if available
    requests_mappings = _get_requests_mappings()
    if requests_mappings:
        mappings.extend(requests_mappings)

    # Add asyncio mappings
    asyncio_mappings = _get_asyncio_mappings()
    if asyncio_mappings:
        mappings.extend(asyncio_mappings)

    # Add standard library mappings
    mappings.extend(_get_stdlib_mappings())

    return mappings


# ----- Library-specific mapping functions -----


def _get_sqlalchemy_mappings() -> list[ExceptionMapping]:
    """Get exception mappings for SQLAlchemy exceptions.

    Returns:
        A list of SQLAlchemy exception mappings or empty list if SQLAlchemy is not available
    """
    if not importlib.util.find_spec("sqlalchemy"):
        return []

    try:
        import sqlalchemy.exc as sa_exc

        # Extract error details from SQLAlchemy exceptions
        def extract_sqlalchemy_context(exc: Exception) -> dict[str, Any]:
            context = default_context_extractor(exc)

            # Handle SQLAlchemy specific attributes
            if hasattr(exc, "statement"):
                context["sql_statement"] = getattr(exc, "statement")
            if hasattr(exc, "params"):
                # Sanitize params to avoid logging sensitive data
                params = getattr(exc, "params")
                if isinstance(params, dict):
                    context["sql_params"] = {
                        k: "***" if k.lower() in ["password", "secret", "token"] else v
                        for k, v in params.items()
                    }
                else:
                    context["sql_params"] = str(params)

            return context

        return [
            ExceptionMapping(
                exception_type=sa_exc.OperationalError,
                target_error_type=DBConnectionError,
                category=ErrorCategory.DB,
                severity=ErrorSeverity.ERROR,
                context_extractor=extract_sqlalchemy_context,
                message_formatter=lambda exc: f"Database operational error: {exc!s}",
                code_extractor=lambda _: "DB_OPERATIONAL_ERROR",
            ),
            ExceptionMapping(
                exception_type=sa_exc.IntegrityError,
                target_error_type=DBError,
                category=ErrorCategory.DB,
                severity=ErrorSeverity.ERROR,
                context_extractor=extract_sqlalchemy_context,
                message_formatter=lambda exc: f"Database integrity error: {exc!s}",
                code_extractor=lambda _: "DB_INTEGRITY_ERROR",
            ),
            ExceptionMapping(
                exception_type=sa_exc.ProgrammingError,
                target_error_type=DBQueryError,
                category=ErrorCategory.DB,
                severity=ErrorSeverity.ERROR,
                context_extractor=extract_sqlalchemy_context,
                message_formatter=lambda exc: f"Database programming error: {exc!s}",
                code_extractor=lambda _: "DB_PROGRAMMING_ERROR",
            ),
            ExceptionMapping(
                exception_type=sa_exc.SQLAlchemyError,
                target_error_type=DBError,
                category=ErrorCategory.DB,
                severity=ErrorSeverity.ERROR,
                context_extractor=extract_sqlalchemy_context,
                message_formatter=lambda exc: f"Database error: {exc!s}",
                code_extractor=lambda _: "DB_ERROR",
            ),
        ]
    except ImportError:
        return []


def _get_pydantic_mappings() -> list[ExceptionMapping]:
    """Get exception mappings for Pydantic exceptions.

    Returns:
        A list of Pydantic exception mappings or empty list if Pydantic is not available
    """
    if not importlib.util.find_spec("pydantic"):
        return []

    try:
        import pydantic

        # Extract validation details from Pydantic exceptions
        def extract_pydantic_context(exc: Exception) -> dict[str, Any]:
            context = default_context_extractor(exc)

            # Handle Pydantic ValidationError
            if hasattr(exc, "errors") and isinstance(exc.errors, list):
                errors = exc.errors
                context["validation_errors"] = errors

                # Extract field names from errors
                fields = []
                for error in errors:
                    if "loc" in error and isinstance(error["loc"], list | tuple):
                        fields.extend([str(loc_part) for loc_part in error["loc"]])

                context["fields"] = list(set(fields))

            return context

        return [
            ExceptionMapping(
                exception_type=pydantic.ValidationError,
                target_error_type=ValidationError,
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.ERROR,
                context_extractor=extract_pydantic_context,
                message_formatter=lambda exc: f"Validation error: {exc!s}",
                code_extractor=lambda _: "VALIDATION_ERROR",
            ),
        ]
    except ImportError:
        return []


def _get_requests_mappings() -> list[ExceptionMapping]:
    """Get exception mappings for requests exceptions.

    Returns:
        A list of requests exception mappings or empty list if requests is not available
    """
    if not importlib.util.find_spec("requests"):
        return []

    try:
        import requests.exceptions as req_exc

        # Extract details from requests exceptions
        def extract_requests_context(exc: Exception) -> dict[str, Any]:
            context = default_context_extractor(exc)

            # Handle requests specific attributes
            if hasattr(exc, "request"):
                request = exc.request
                if hasattr(request, "url"):
                    context["request_url"] = request.url
                if hasattr(request, "method"):
                    context["request_method"] = request.method

            if hasattr(exc, "response"):
                response = exc.response
                if hasattr(response, "status_code"):
                    context["response_status_code"] = response.status_code
                if hasattr(response, "reason"):
                    context["response_reason"] = response.reason

            return context

        return [
            ExceptionMapping(
                exception_type=req_exc.ConnectionError,
                target_error_type=APIError,
                category=ErrorCategory.API,
                severity=ErrorSeverity.ERROR,
                context_extractor=extract_requests_context,
                message_formatter=lambda exc: f"API connection error: {exc!s}",
                code_extractor=lambda _: "API_CONNECTION_ERROR",
            ),
            ExceptionMapping(
                exception_type=req_exc.Timeout,
                target_error_type=APIError,
                category=ErrorCategory.API,
                severity=ErrorSeverity.ERROR,
                context_extractor=extract_requests_context,
                message_formatter=lambda exc: f"API timeout error: {exc!s}",
                code_extractor=lambda _: "API_TIMEOUT_ERROR",
            ),
            ExceptionMapping(
                exception_type=req_exc.HTTPError,
                target_error_type=APIError,
                category=ErrorCategory.API,
                severity=ErrorSeverity.ERROR,
                context_extractor=extract_requests_context,
                message_formatter=lambda exc: f"API HTTP error: {exc!s}",
                code_extractor=lambda _: "API_HTTP_ERROR",
            ),
            ExceptionMapping(
                exception_type=req_exc.RequestException,
                target_error_type=APIError,
                category=ErrorCategory.API,
                severity=ErrorSeverity.ERROR,
                context_extractor=extract_requests_context,
                message_formatter=lambda exc: f"API request error: {exc!s}",
                code_extractor=lambda _: "API_REQUEST_ERROR",
            ),
        ]
    except ImportError:
        return []


def _get_asyncio_mappings() -> list[ExceptionMapping]:
    """Get exception mappings for asyncio exceptions.

    Returns:
        A list of asyncio exception mappings
    """
    import asyncio

    return [
        ExceptionMapping(
            exception_type=asyncio.TimeoutError,
            target_error_type=UnoError,
            category=ErrorCategory.INTERNAL,
            severity=ErrorSeverity.ERROR,
            message_formatter=lambda _: "Operation timed out",
            code_extractor=lambda _: "ASYNCIO_TIMEOUT",
        ),
        ExceptionMapping(
            exception_type=asyncio.CancelledError,
            target_error_type=UnoError,
            category=ErrorCategory.INTERNAL,
            severity=ErrorSeverity.WARNING,
            message_formatter=lambda _: "Operation was cancelled",
            code_extractor=lambda _: "ASYNCIO_CANCELLED",
        ),
    ]


def _get_stdlib_mappings() -> list[ExceptionMapping]:
    """Get exception mappings for standard library exceptions.

    Returns:
        A list of standard library exception mappings
    """
    return [
        # File operations
        ExceptionMapping(
            exception_type=FileNotFoundError,
            target_error_type=UnoError,
            category=ErrorCategory.INTERNAL,
            severity=ErrorSeverity.ERROR,
            message_formatter=lambda exc: f"File not found: {exc!s}",
            code_extractor=lambda _: "FILE_NOT_FOUND",
        ),
        ExceptionMapping(
            exception_type=PermissionError,
            target_error_type=UnoError,
            category=ErrorCategory.SECURITY,
            severity=ErrorSeverity.ERROR,
            message_formatter=lambda exc: f"Permission denied: {exc!s}",
            code_extractor=lambda _: "PERMISSION_DENIED",
        ),
        # JSON operations
        ExceptionMapping(
            exception_type=ValueError,
            target_error_type=ValidationError,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.ERROR,
            context_extractor=lambda exc: f"error_details: {exc!s}",
            message_formatter=lambda exc: f"Value error: {exc!s}",
            code_extractor=lambda _: "VALUE_ERROR",
        ),
        # Network operations
        ExceptionMapping(
            exception_type=ConnectionError,
            target_error_type=APIError,
            category=ErrorCategory.API,
            severity=ErrorSeverity.ERROR,
            message_formatter=lambda exc: f"Connection error: {exc!s}",
            code_extractor=lambda _: "CONNECTION_ERROR",
        ),
        ExceptionMapping(
            exception_type=TimeoutError,
            target_error_type=APIError,
            category=ErrorCategory.API,
            severity=ErrorSeverity.ERROR,
            message_formatter=lambda exc: f"Timeout error: {exc!s}",
            code_extractor=lambda _: "TIMEOUT_ERROR",
        ),
        # Other common exceptions
        ExceptionMapping(
            exception_type=KeyError,
            target_error_type=UnoError,
            category=ErrorCategory.INTERNAL,
            severity=ErrorSeverity.ERROR,
            message_formatter=lambda exc: f"Key error: {exc!s}",
            code_extractor=lambda _: "KEY_ERROR",
        ),
        ExceptionMapping(
            exception_type=TypeError,
            target_error_type=ValidationError,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.ERROR,
            message_formatter=lambda exc: f"Type error: {exc!s}",
            code_extractor=lambda _: "TYPE_ERROR",
        ),
        ExceptionMapping(
            exception_type=AttributeError,
            target_error_type=UnoError,
            category=ErrorCategory.INTERNAL,
            severity=ErrorSeverity.ERROR,
            message_formatter=lambda exc: f"Attribute error: {exc!s}",
            code_extractor=lambda _: "ATTRIBUTE_ERROR",
        ),
        ExceptionMapping(
            exception_type=IndexError,
            target_error_type=UnoError,
            category=ErrorCategory.INTERNAL,
            severity=ErrorSeverity.ERROR,
            message_formatter=lambda exc: f"Index error: {exc!s}",
            code_extractor=lambda _: "INDEX_ERROR",
        ),
    ]


# ----- Specialized wrappers for common use cases -----


def wrap_validation_exception(
    exception: Exception,
    message: str | None = None,
    field_name: str | None = None,
    field_value: Any | None = None,
    **context: Any,
) -> ValidationError:
    """Wrap an exception as a ValidationError.

    Args:
        exception: The exception to wrap
        message: Optional message override
        field_name: Optional field name that failed validation
        field_value: Optional value that failed validation
        **context: Additional context information

    Returns:
        A ValidationError instance
    """
    ctx = context.copy()
    if field_name:
        ctx["field_name"] = field_name
    if field_value is not None:
        ctx["field_value"] = str(field_value)

    return cast(
        ValidationError,
        wrap_exception(
            exception=exception,
            message=message,
            error_class=ValidationError,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.ERROR,
            **ctx,
        ),
    )


def wrap_database_exception(
    exception: Exception,
    message: str | None = None,
    query: str | None = None,
    params: dict[str, Any] | None = None,
    **context: Any,
) -> DBError:
    """Wrap an exception as a DBError.

    Args:
        exception: The exception to wrap
        message: Optional message override
        query: Optional SQL query that caused the error
        params: Optional query parameters
        **context: Additional context information

    Returns:
        A DBError instance
    """
    ctx = context.copy()
    if query:
        ctx["query"] = query
    if params:
        # Sanitize params to avoid logging sensitive data
        ctx["params"] = {
            k: "***" if k.lower() in ["password", "secret", "token"] else v
            for k, v in params.items()
        }

    return cast(
        DBError,
        wrap_exception(
            exception=exception,
            message=message,
            error_class=DBError,
            category=ErrorCategory.DB,
            severity=ErrorSeverity.ERROR,
            **ctx,
        ),
    )


def wrap_api_exception(
    exception: Exception,
    message: str | None = None,
    url: str | None = None,
    method: str | None = None,
    status_code: int | None = None,
    **context: Any,
) -> APIError:
    """Wrap an exception as an APIError.

    Args:
        exception: The exception to wrap
        message: Optional message override
        url: Optional URL that caused the error
        method: Optional HTTP method
        status_code: Optional HTTP status code
        **context: Additional context information

    Returns:
        An APIError instance
    """
    ctx = context.copy()
    if url:
        ctx["url"] = url
    if method:
        ctx["method"] = method
    if status_code:
        ctx["status_code"] = status_code

    return cast(
        APIError,
        wrap_exception(
            exception=exception,
            message=message,
            error_class=APIError,
            category=ErrorCategory.API,
            severity=ErrorSeverity.ERROR,
            **ctx,
        ),
    )


def wrap_security_exception(
    exception: Exception,
    message: str | None = None,
    username: str | None = None,
    resource: str | None = None,
    action: str | None = None,
    **context: Any,
) -> SecurityError:
    """Wrap an exception as a SecurityError.

    Args:
        exception: The exception to wrap
        message: Optional message override
        username: Optional username related to the error
        resource: Optional resource being accessed
        action: Optional action being performed
        **context: Additional context information

    Returns:
        A SecurityError instance
    """
    ctx = context.copy()
    if username:
        ctx["username"] = username
    if resource:
        ctx["resource"] = resource
    if action:
        ctx["action"] = action

    return cast(
        SecurityError,
        wrap_exception(
            exception=exception,
            message=message,
            error_class=SecurityError,
            category=ErrorCategory.SECURITY,
            severity=ErrorSeverity.ERROR,
            **ctx,
        ),
    )


def wrap_event_exception(
    exception: Exception,
    message: str | None = None,
    event_type: str | None = None,
    handler_name: str | None = None,
    **context: Any,
) -> EventError:
    """Wrap an exception as an EventError.

    Args:
        exception: The exception to wrap
        message: Optional message override
        event_type: Optional event type
        handler_name: Optional handler name
        **context: Additional context information

    Returns:
        An EventError instance
    """
    ctx = context.copy()
    if event_type:
        ctx["event_type"] = event_type
    if handler_name:
        ctx["handler_name"] = handler_name

    return cast(
        EventError,
        wrap_exception(
            exception=exception,
            message=message,
            error_class=EventError,
            category=ErrorCategory.EVENT,
            severity=ErrorSeverity.ERROR,
            **ctx,
        ),
    )


# ----- Context decorators for try-except blocks -----


def with_error_context(**context: Any) -> Callable[[Callable], Callable]:
    """Decorator that adds context to any UnoError raised in the decorated function.

    Args:
        **context: Context to add to any raised UnoError

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except UnoError as e:
                # Canonical Uno error enrichment: raise a new error instance with merged context
                raise e.with_context(context)
            except Exception as e:
                # Wrap other exceptions with context
                raise wrap_exception(e, **context)

        return wrapper

    return decorator


def with_error_mapping(
    mappings: list[ExceptionMapping],
) -> Callable[[Callable], Callable]:
    """Decorator that maps exceptions raised in the decorated function according to the provided mappings.

    Args:
        mappings: List of exception mappings to use

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except UnoError:
                # Don't wrap UnoErrors
                raise
            except Exception as e:
                # Wrap other exceptions
                raise wrap_exception(e, mappings=mappings)

        return wrapper

    return decorator
