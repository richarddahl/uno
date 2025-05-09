# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Factory functions for creating component-specific errors.

This module provides factory functions to simplify the creation of standardized
error instances across the Uno framework. These factories ensure consistent
error messages, error codes, and context enrichment.
"""

from __future__ import annotations
from typing import Any, Optional, Dict, Type, TypeVar, cast

from uno.errors.base import ErrorCategory, ErrorSeverity, UnoError
from uno.errors.component_errors import (
    APIError,
    APIResourceNotFoundError,
    APIValidationError,
    ConfigError,
    ConfigMissingKeyError,
    ConfigFileNotFoundError,
    DBError,
    DBConnectionError,
    DBQueryError,
    DIError,
    DIServiceNotRegisteredError,
    DICircularDependencyError,
    EventError,
    EventPublishError,
    EventHandlerError,
    SecurityError,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    SchemaValidationError,
    InputValidationError,
)


# =============================================================================
# API Error Factories
# =============================================================================


def api_error(message: str, error_code: str | None = None, **context: Any) -> APIError:
    """Create a generic API error.

    Args:
        message: Human-readable error message
        error_code: Error code without prefix
        **context: Additional context information

    Returns:
        An APIError instance
    """
    return APIError(message=message, error_code=error_code, **context)


def api_resource_not_found(
    resource_type: str, resource_id: Any, message: str | None = None, **context: Any
) -> APIResourceNotFoundError:
    """Create an API resource not found error.

    Args:
        resource_type: Type of resource that was not found
        resource_id: ID of the resource
        message: Optional custom message
        **context: Additional context information

    Returns:
        An APIResourceNotFoundError instance
    """
    return APIResourceNotFoundError(
        resource_type=resource_type, resource_id=resource_id, message=message, **context
    )


def api_validation_error(
    message: str,
    field: str | None = None,
    value: Any | None = None,
    **context: Any,
) -> APIValidationError:
    """Create an API validation error.

    Args:
        message: Validation error message
        field: Name of the field that failed validation
        value: Value that failed validation
        **context: Additional context information

    Returns:
        An APIValidationError instance
    """
    return APIValidationError(message=message, field=field, value=value, **context)


# =============================================================================
# Configuration Error Factories
# =============================================================================


def config_error(
    message: str, error_code: str | None = None, **context: Any
) -> ConfigError:
    """Create a generic configuration error.

    Args:
        message: Human-readable error message
        error_code: Error code without prefix
        **context: Additional context information

    Returns:
        A ConfigError instance
    """
    return ConfigError(message=message, error_code=error_code, **context)


def config_missing_key(
    key: str, message: str | None = None, **context: Any
) -> ConfigMissingKeyError:
    """Create a configuration missing key error.

    Args:
        key: The configuration key that is missing
        message: Optional custom message
        **context: Additional context information

    Returns:
        A ConfigMissingKeyError instance
    """
    return ConfigMissingKeyError(key=key, message=message, **context)


def config_file_not_found(
    file_path: str, message: str | None = None, **context: Any
) -> ConfigFileNotFoundError:
    """Create a configuration file not found error.

    Args:
        file_path: Path to the configuration file
        message: Optional custom message
        **context: Additional context information

    Returns:
        A ConfigFileNotFoundError instance
    """
    return ConfigFileNotFoundError(file_path=file_path, message=message, **context)


# =============================================================================
# Database Error Factories
# =============================================================================


def db_error(message: str, error_code: str | None = None, **context: Any) -> DBError:
    """Create a generic database error.

    Args:
        message: Human-readable error message
        error_code: Error code without prefix
        **context: Additional context information

    Returns:
        A DBError instance
    """
    return DBError(message=message, error_code=error_code, **context)


def db_connection_error(
    message: str = "Failed to connect to database",
    connection_string: str | None = None,
    **context: Any,
) -> DBConnectionError:
    """Create a database connection error.

    Args:
        message: Human-readable error message
        connection_string: Database connection string (will be sanitized)
        **context: Additional context information

    Returns:
        A DBConnectionError instance
    """
    return DBConnectionError(
        message=message, connection_string=connection_string, **context
    )


def db_query_error(
    message: str,
    query: str | None = None,
    params: dict[str, Any] | None = None,
    **context: Any,
) -> DBQueryError:
    """Create a database query error.

    Args:
        message: Human-readable error message
        query: The SQL query that failed
        params: Query parameters (sensitive data will be sanitized)
        **context: Additional context information

    Returns:
        A DBQueryError instance
    """
    return DBQueryError(message=message, query=query, params=params, **context)


# =============================================================================
# Dependency Injection Error Factories
# =============================================================================


def di_error(message: str, error_code: str | None = None, **context: Any) -> DIError:
    """Create a generic dependency injection error.

    Args:
        message: Human-readable error message
        error_code: Error code without prefix
        **context: Additional context information

    Returns:
        A DIError instance
    """
    return DIError(message=message, error_code=error_code, **context)


def di_service_not_registered(
    service_type: str, message: str | None = None, **context: Any
) -> DIServiceNotRegisteredError:
    """Create a service not registered error.

    Args:
        service_type: Type of service that was not registered
        message: Optional custom message
        **context: Additional context information

    Returns:
        A DIServiceNotRegisteredError instance
    """
    return DIServiceNotRegisteredError(
        service_type=service_type, message=message, **context
    )


def di_circular_dependency(
    dependency_chain: list[str], message: str | None = None, **context: Any
) -> DICircularDependencyError:
    """Create a circular dependency error.

    Args:
        dependency_chain: List of service types forming the circular dependency
        message: Optional custom message
        **context: Additional context information

    Returns:
        A DICircularDependencyError instance
    """
    return DICircularDependencyError(
        dependency_chain=dependency_chain, message=message, **context
    )


# =============================================================================
# Event Error Factories
# =============================================================================


def event_error(
    message: str, error_code: str | None = None, **context: Any
) -> EventError:
    """Create a generic event error.

    Args:
        message: Human-readable error message
        error_code: Error code without prefix
        **context: Additional context information

    Returns:
        An EventError instance
    """
    return EventError(message=message, error_code=error_code, **context)


def event_publish_error(
    event_type: str, reason: str, message: str | None = None, **context: Any
) -> EventPublishError:
    """Create an event publish error.

    Args:
        event_type: Type of the event
        reason: Reason for the publish failure
        message: Optional custom message
        **context: Additional context information

    Returns:
        An EventPublishError instance
    """
    return EventPublishError(
        event_type=event_type, reason=reason, message=message, **context
    )


def event_handler_error(
    event_type: str,
    handler_name: str,
    reason: str,
    message: str | None = None,
    **context: Any,
) -> EventHandlerError:
    """Create an event handler error.

    Args:
        event_type: Type of the event
        handler_name: Name of the handler that failed
        reason: Reason for the handler failure
        message: Optional custom message
        **context: Additional context information

    Returns:
        An EventHandlerError instance
    """
    return EventHandlerError(
        event_type=event_type,
        handler_name=handler_name,
        reason=reason,
        message=message,
        **context,
    )


# =============================================================================
# Security Error Factories
# =============================================================================


def security_error(
    message: str, error_code: str | None = None, **context: Any
) -> SecurityError:
    """Create a generic security error.

    Args:
        message: Human-readable error message
        error_code: Error code without prefix
        **context: Additional context information

    Returns:
        A SecurityError instance
    """
    return SecurityError(message=message, error_code=error_code, **context)


def authentication_error(
    message: str = "Authentication failed",
    username: str | None = None,
    **context: Any,
) -> AuthenticationError:
    """Create an authentication error.

    Args:
        message: Human-readable error message
        username: Username that failed authentication
        **context: Additional context information

    Returns:
        An AuthenticationError instance
    """
    return AuthenticationError(message=message, username=username, **context)


def authorization_error(
    message: str = "Authorization failed",
    username: str | None = None,
    resource: str | None = None,
    action: str | None = None,
    **context: Any,
) -> AuthorizationError:
    """Create an authorization error.

    Args:
        message: Human-readable error message
        username: Username that failed authorization
        resource: Resource being accessed
        action: Action being performed
        **context: Additional context information

    Returns:
        An AuthorizationError instance
    """
    return AuthorizationError(
        message=message, username=username, resource=resource, action=action, **context
    )


# =============================================================================
# Validation Error Factories
# =============================================================================


def validation_error(
    message: str, error_code: str | None = None, **context: Any
) -> ValidationError:
    """Create a generic validation error.

    Args:
        message: Human-readable error message
        error_code: Error code without prefix
        **context: Additional context information

    Returns:
        A ValidationError instance
    """
    return ValidationError(message=message, error_code=error_code, **context)


def schema_validation_error(
    message: str,
    schema_name: str | None = None,
    field_name: str | None = None,
    field_value: Any | None = None,
    **context: Any,
) -> SchemaValidationError:
    """Create a schema validation error.

    Args:
        message: Human-readable error message
        schema_name: Name of the schema
        field_name: Name of the field that failed validation
        field_value: Value that failed validation
        **context: Additional context information

    Returns:
        A SchemaValidationError instance
    """
    return SchemaValidationError(
        message=message,
        schema_name=schema_name,
        field_name=field_name,
        field_value=field_value,
        **context,
    )


def input_validation_error(
    message: str,
    field_name: str | None = None,
    field_value: Any | None = None,
    **context: Any,
) -> InputValidationError:
    """Create an input validation error.

    Args:
        message: Human-readable error message
        field_name: Name of the field that failed validation
        field_value: Value that failed validation
        **context: Additional context information

    Returns:
        An InputValidationError instance
    """
    return InputValidationError(
        message=message, field_name=field_name, field_value=field_value, **context
    )
