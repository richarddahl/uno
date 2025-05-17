# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Advanced external exception wrapping utilities for the Uno framework.

This module provides specialized utilities for wrapping external exceptions
from various libraries and frameworks with Uno error types, ensuring proper
context capturing, categorization, and error code mapping.
"""

from __future__ import annotations

import importlib.util
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar, cast

from uno.errors import UnoError, ErrorCode, ErrorSeverity

T = TypeVar("T", bound=UnoError)


@dataclass
class ExceptionMapping:
    """Mapping configuration for external exception types to Uno error types."""

    exception_type: type[Exception]
    target_error_type: type[UnoError]
    error_code: ErrorCode
    severity: ErrorSeverity = ErrorSeverity.ERROR
    context_extractor: Callable[[Exception], dict[str, Any]] | None = None
    message_formatter: Callable[[Exception], str] | None = None


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


def error_context_from_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Extract relevant context information from a dictionary.

    This utility helps create standardized context information
    from various data structures.

    Args:
        data: Dictionary containing data to extract context from

    Returns:
        Dictionary with context information
    """
    # Filter out None values and create a shallow copy
    return {k: v for k, v in data.items() if v is not None}


async def wrap_exception(
    exception: Exception,
    code: ErrorCode,
    message: str | None = None,
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
        code: Error code for the wrapped exception (includes category)
        severity: Error severity
        error_class: Specific error class to instantiate
        mappings: Optional list of exception mappings to use
        extract_context: Whether to extract context from the exception
        **context: Additional context information

    Returns:
        A new UnoError instance with the exception as its cause
    """
    # First try to find a mapping for this exception type
    mapping = await _find_matching_mapping(
        exception, mappings or await _get_default_mappings()
    )

    # Prepare the error information
    target_error_class = error_class or (
        mapping.target_error_type if mapping else UnoError
    )
    final_code = code
    if mapping and not code:
        final_code = mapping.error_code
    final_severity = severity or (mapping.severity if mapping else ErrorSeverity.ERROR)

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
        severity=final_severity,
        context=combined_context,  # Pass as context parameter rather than kwargs
    )

    # Set the cause
    error.__cause__ = exception

    # Add stack trace information if available
    if hasattr(exception, "__traceback__") and exception.__traceback__:
        error.traceback_str = "".join(traceback.format_tb(exception.__traceback__))

    return error


async def _find_matching_mapping(
    exception: Exception, mappings: list[ExceptionMapping]
) -> ExceptionMapping | None:
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


async def _get_default_mappings() -> list[ExceptionMapping]:
    """Get default mappings for common external exceptions.

    Returns:
        A list of default exception mappings
    """
    mappings = []

    # Add SQLAlchemy mappings if available
    sqlalchemy_mappings = await _get_sqlalchemy_mappings()
    if sqlalchemy_mappings:
        mappings.extend(sqlalchemy_mappings)

    # Add Pydantic mappings if available
    pydantic_mappings = await _get_pydantic_mappings()
    if pydantic_mappings:
        mappings.extend(pydantic_mappings)

    # Add requests mappings if available
    requests_mappings = await _get_requests_mappings()
    if requests_mappings:
        mappings.extend(requests_mappings)

    # Add asyncio mappings
    asyncio_mappings = await _get_asyncio_mappings()
    if asyncio_mappings:
        mappings.extend(asyncio_mappings)

    # Add standard library mappings
    mappings.extend(await _get_stdlib_mappings())

    return mappings


# ----- Library-specific mapping functions -----


async def _get_sqlalchemy_mappings() -> list[ExceptionMapping]:
    """Get exception mappings for SQLAlchemy exceptions.

    Returns:
        A list of SQLAlchemy exception mappings or empty list if SQLAlchemy is not available
    """
    if not importlib.util.find_spec("sqlalchemy"):
        return []

    try:
        import sqlalchemy.exc as sa_exc
        from uno.errors.codes import ErrorCode, get_code_by_name

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
                error_code=get_code_by_name("DB_OPERATIONAL_ERROR"),
                severity=ErrorSeverity.ERROR,
                context_extractor=extract_sqlalchemy_context,
                message_formatter=lambda exc: f"Database operational error: {exc!s}",
            ),
            ExceptionMapping(
                exception_type=sa_exc.IntegrityError,
                target_error_type=DBError,
                error_code=get_code_by_name("DB_INTEGRITY_ERROR"),
                severity=ErrorSeverity.ERROR,
                context_extractor=extract_sqlalchemy_context,
                message_formatter=lambda exc: f"Database integrity error: {exc!s}",
            ),
            ExceptionMapping(
                exception_type=sa_exc.ProgrammingError,
                target_error_type=DBQueryError,
                error_code=get_code_by_name("DB_PROGRAMMING_ERROR"),
                severity=ErrorSeverity.ERROR,
                context_extractor=extract_sqlalchemy_context,
                message_formatter=lambda exc: f"Database programming error: {exc!s}",
            ),
            ExceptionMapping(
                exception_type=sa_exc.SQLAlchemyError,
                target_error_type=DBError,
                error_code=get_code_by_name("DB_ERROR"),
                severity=ErrorSeverity.ERROR,
                context_extractor=extract_sqlalchemy_context,
                message_formatter=lambda exc: f"Database error: {exc!s}",
            ),
        ]
    except ImportError:
        return []


async def _get_pydantic_mappings() -> list[ExceptionMapping]:
    """Get exception mappings for Pydantic exceptions.

    Returns:
        A list of Pydantic exception mappings or empty list if Pydantic is not available
    """
    if not importlib.util.find_spec("pydantic"):
        return []

    try:
        import pydantic
        from uno.errors.codes import get_code_by_name

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
                error_code=get_code_by_name("VALIDATION_ERROR"),
                severity=ErrorSeverity.ERROR,
                context_extractor=extract_pydantic_context,
                message_formatter=lambda exc: f"Validation error: {exc!s}",
            ),
        ]
    except ImportError:
        return []


async def _get_requests_mappings() -> list[ExceptionMapping]:
    """Get exception mappings for requests exceptions.

    Returns:
        A list of requests exception mappings or empty list if requests is not available
    """
    if not importlib.util.find_spec("requests"):
        return []

    try:
        import requests.exceptions as req_exc
        from uno.errors.codes import get_code_by_name

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
                error_code=get_code_by_name("API_CONNECTION_ERROR"),
                severity=ErrorSeverity.ERROR,
                context_extractor=extract_requests_context,
                message_formatter=lambda exc: f"API connection error: {exc!s}",
            ),
            ExceptionMapping(
                exception_type=req_exc.Timeout,
                target_error_type=APIError,
                error_code=get_code_by_name("API_TIMEOUT_ERROR"),
                severity=ErrorSeverity.ERROR,
                context_extractor=extract_requests_context,
                message_formatter=lambda exc: f"API timeout error: {exc!s}",
            ),
            ExceptionMapping(
                exception_type=req_exc.HTTPError,
                target_error_type=APIError,
                error_code=get_code_by_name("API_HTTP_ERROR"),
                severity=ErrorSeverity.ERROR,
                context_extractor=extract_requests_context,
                message_formatter=lambda exc: f"API HTTP error: {exc!s}",
            ),
            ExceptionMapping(
                exception_type=req_exc.RequestException,
                target_error_type=APIError,
                error_code=get_code_by_name("API_REQUEST_ERROR"),
                severity=ErrorSeverity.ERROR,
                context_extractor=extract_requests_context,
                message_formatter=lambda exc: f"API request error: {exc!s}",
            ),
        ]
    except ImportError:
        return []


async def _get_asyncio_mappings() -> list[ExceptionMapping]:
    """Get exception mappings for asyncio exceptions.

    Returns:
        A list of asyncio exception mappings
    """
    import asyncio
    from uno.errors.codes import get_code_by_name

    return [
        ExceptionMapping(
            exception_type=asyncio.TimeoutError,
            target_error_type=UnoError,
            error_code=get_code_by_name("ASYNCIO_TIMEOUT"),
            severity=ErrorSeverity.ERROR,
            message_formatter=lambda _: "Operation timed out",
        ),
        ExceptionMapping(
            exception_type=asyncio.CancelledError,
            target_error_type=UnoError,
            error_code=get_code_by_name("ASYNCIO_CANCELLED"),
            severity=ErrorSeverity.WARNING,
            message_formatter=lambda _: "Operation was cancelled",
        ),
    ]


async def _get_stdlib_mappings() -> list[ExceptionMapping]:
    """Get exception mappings for standard library exceptions.

    Returns:
        A list of standard library exception mappings
    """
    from uno.errors.codes import get_code_by_name

    return [
        # File operations
        ExceptionMapping(
            exception_type=FileNotFoundError,
            target_error_type=UnoError,
            error_code=get_code_by_name("FILE_NOT_FOUND"),
            severity=ErrorSeverity.ERROR,
            message_formatter=lambda exc: f"File not found: {exc!s}",
        ),
        ExceptionMapping(
            exception_type=PermissionError,
            target_error_type=UnoError,
            error_code=get_code_by_name("PERMISSION_DENIED"),
            severity=ErrorSeverity.ERROR,
            message_formatter=lambda exc: f"Permission denied: {exc!s}",
        ),
        # JSON operations
        ExceptionMapping(
            exception_type=ValueError,
            target_error_type=ValidationError,
            error_code=get_code_by_name("VALUE_ERROR"),
            severity=ErrorSeverity.ERROR,
            context_extractor=lambda exc: f"error_details: {exc!s}",
            message_formatter=lambda exc: f"Value error: {exc!s}",
        ),
        # Network operations
        ExceptionMapping(
            exception_type=ConnectionError,
            target_error_type=APIError,
            error_code=get_code_by_name("CONNECTION_ERROR"),
            severity=ErrorSeverity.ERROR,
            message_formatter=lambda exc: f"Connection error: {exc!s}",
        ),
        ExceptionMapping(
            exception_type=TimeoutError,
            target_error_type=APIError,
            error_code=get_code_by_name("TIMEOUT_ERROR"),
            severity=ErrorSeverity.ERROR,
            message_formatter=lambda exc: f"Timeout error: {exc!s}",
        ),
        # Other common exceptions
        ExceptionMapping(
            exception_type=KeyError,
            target_error_type=UnoError,
            error_code=get_code_by_name("KEY_ERROR"),
            severity=ErrorSeverity.ERROR,
            message_formatter=lambda exc: f"Key error: {exc!s}",
        ),
        ExceptionMapping(
            exception_type=TypeError,
            target_error_type=ValidationError,
            error_code=get_code_by_name("TYPE_ERROR"),
            severity=ErrorSeverity.ERROR,
            message_formatter=lambda exc: f"Type error: {exc!s}",
        ),
        ExceptionMapping(
            exception_type=AttributeError,
            target_error_type=UnoError,
            error_code=get_code_by_name("ATTRIBUTE_ERROR"),
            severity=ErrorSeverity.ERROR,
            message_formatter=lambda exc: f"Attribute error: {exc!s}",
        ),
        ExceptionMapping(
            exception_type=IndexError,
            target_error_type=UnoError,
            error_code=get_code_by_name("INDEX_ERROR"),
            severity=ErrorSeverity.ERROR,
            message_formatter=lambda exc: f"Index error: {exc!s}",
        ),
    ]


# ----- Specialized wrappers for common use cases -----


async def wrap_validation_exception(
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
    from uno.errors.codes import get_code_by_name

    ctx = context.copy()
    if field_name:
        ctx["field_name"] = field_name
    if field_value is not None:
        ctx["field_value"] = str(field_value)

    return cast(
        ValidationError,
        await wrap_exception(
            exception=exception,
            message=message,
            code=get_code_by_name("VALIDATION_ERROR"),
            error_class=ValidationError,
            severity=ErrorSeverity.ERROR,
            **ctx,
        ),
    )


async def wrap_database_exception(
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
    from uno.errors.codes import get_code_by_name

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
        await wrap_exception(
            exception=exception,
            message=message,
            code=get_code_by_name("DB_ERROR"),
            error_class=DBError,
            severity=ErrorSeverity.ERROR,
            **ctx,
        ),
    )


async def wrap_api_exception(
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
    from uno.errors.codes import get_code_by_name

    ctx = context.copy()
    if url:
        ctx["url"] = url
    if method:
        ctx["method"] = method
    if status_code:
        ctx["status_code"] = status_code

    return cast(
        APIError,
        await wrap_exception(
            exception=exception,
            message=message,
            code=get_code_by_name("API_ERROR"),
            error_class=APIError,
            severity=ErrorSeverity.ERROR,
            **ctx,
        ),
    )


async def wrap_security_exception(
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
    from uno.errors.codes import get_code_by_name

    ctx = context.copy()
    if username:
        ctx["username"] = username
    if resource:
        ctx["resource"] = resource
    if action:
        ctx["action"] = action

    return cast(
        SecurityError,
        await wrap_exception(
            exception=exception,
            message=message,
            code=get_code_by_name("SECURITY_ERROR"),
            error_class=SecurityError,
            severity=ErrorSeverity.ERROR,
            **ctx,
        ),
    )


async def wrap_event_exception(
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
    from uno.errors.codes import get_code_by_name

    ctx = context.copy()
    if event_type:
        ctx["event_type"] = event_type
    if handler_name:
        ctx["handler_name"] = handler_name

    return cast(
        EventError,
        await wrap_exception(
            exception=exception,
            message=message,
            code=get_code_by_name("EVENT_ERROR"),
            error_class=EventError,
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
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except UnoError as e:
                # Canonical Uno error enrichment: raise a new error instance with merged context
                raise e.with_context(context)
            except Exception as e:
                # Wrap other exceptions with context
                raise await wrap_exception(e, **context)

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
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except UnoError:
                # Don't wrap UnoErrors
                raise
            except Exception as e:
                # Wrap other exceptions
                raise await wrap_exception(e, mappings=mappings)

        return wrapper

    return decorator


# Update the module's exports
__all__ = [
    "ExceptionMapping",
    "wrap_exception",
    "wrap_validation_exception",
    "wrap_database_exception",
    "wrap_api_exception",
    "wrap_security_exception",
    "wrap_event_exception",
    "with_error_context",
    "with_error_mapping",
    "error_context_from_dict",
    "default_message_formatter",
    "default_context_extractor",
]
