# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Component-specific error hierarchies for the Uno framework.

This module defines a comprehensive hierarchy of error classes for all major
components in the Uno framework. It provides specialized error types with
standardized error code prefixes, context enrichment, and category classification.

All component errors inherit from UnoError and provide additional context and
structured error codes specific to their component area.
"""

from __future__ import annotations
from typing import Any, Final, Optional, Type, Dict, TypeVar, cast

from uno.errors.base import ErrorCategory, ErrorSeverity, UnoError

# =============================================================================
# Common Error Base Classes
# =============================================================================


class ComponentError(UnoError):
    """Base class for all component-specific errors.

    Adds standardized error code prefixing and component categorization.
    """

    # Override in subclasses
    PREFIX: str = "COMP"
    CATEGORY: ErrorCategory = ErrorCategory.INTERNAL

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        **context: Any,
    ) -> None:
        """Initialize a component-specific error.

        Args:
            message: Human-readable error message
            error_code: Error code without prefix (will be prefixed automatically)
            severity: How severe this error is
            **context: Additional context information
        """
        super().__init__(
            message=message,
            error_code=(
                f"{self.PREFIX}_{error_code}" if error_code else f"{self.PREFIX}_ERROR"
            ),
            category=self.CATEGORY,
            severity=severity,
            **context,
        )


# =============================================================================
# API Errors
# =============================================================================


class APIError(ComponentError):
    """Base class for all API-related errors."""

    PREFIX: str = "API"
    CATEGORY: ErrorCategory = ErrorCategory.API


class APIAuthenticationError(APIError):
    """Raised when API authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: str | None = "AUTH_FAILED",
        **context: Any,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            **context,
        )


class APIAuthorizationError(APIError):
    """Raised when API authorization fails."""

    def __init__(
        self,
        message: str = "Authorization failed",
        resource: str | None = None,
        action: str | None = None,
        error_code: str | None = "AUTH_DENIED",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if resource:
            ctx["resource"] = resource
        if action:
            ctx["action"] = action

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )


class APIValidationError(APIError):
    """Raised when API input validation fails."""

    def __init__(
        self,
        message: str = "Validation failed",
        field: str | None = None,
        value: Any | None = None,
        error_code: str | None = "VALIDATION_ERROR",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if field:
            ctx["field"] = field
        if value is not None:
            ctx["value"] = str(value)

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )


class APIResourceNotFoundError(APIError):
    """Raised when an API resource is not found."""

    def __init__(
        self,
        resource_type: str,
        resource_id: Any,
        message: str | None = None,
        error_code: str | None = "RESOURCE_NOT_FOUND",
        **context: Any,
    ) -> None:
        message = message or f"{resource_type} with ID '{resource_id}' not found"

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            resource_type=resource_type,
            resource_id=str(resource_id),
            **context,
        )


class APIRateLimitError(APIError):
    """Raised when API rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        limit: int | None = None,
        reset_after: int | None = None,
        error_code: str | None = "RATE_LIMIT_EXCEEDED",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if limit:
            ctx["limit"] = limit
        if reset_after:
            ctx["reset_after"] = reset_after

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )


# =============================================================================
# Configuration Errors
# =============================================================================


class ConfigError(ComponentError):
    """Base class for all configuration-related errors."""

    PREFIX: str = "CONFIG"
    CATEGORY: ErrorCategory = ErrorCategory.CONFIG


class ConfigValidationError(ConfigError):
    """Raised when configuration validation fails."""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        config_value: Any | None = None,
        error_code: str | None = "VALIDATION_ERROR",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if config_key:
            ctx["config_key"] = config_key
        if config_value is not None:
            ctx["config_value"] = str(config_value)

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )


class ConfigFileNotFoundError(ConfigError):
    """Raised when a configuration file is not found."""

    def __init__(
        self,
        file_path: str,
        message: str | None = None,
        error_code: str | None = "FILE_NOT_FOUND",
        **context: Any,
    ) -> None:
        message = message or f"Configuration file not found: {file_path}"

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            file_path=file_path,
            **context,
        )


class ConfigParseError(ConfigError):
    """Raised when parsing a configuration file fails."""

    def __init__(
        self,
        file_path: str,
        reason: str,
        line_number: int | None = None,
        error_code: str | None = "PARSE_ERROR",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if line_number is not None:
            ctx["line_number"] = line_number

        message = f"Failed to parse configuration file {file_path}: {reason}"
        if line_number is not None:
            message += f" at line {line_number}"

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            file_path=file_path,
            reason=reason,
            **ctx,
        )


class ConfigMissingKeyError(ConfigError):
    """Raised when a required configuration key is missing."""

    def __init__(
        self,
        key: str,
        message: str | None = None,
        error_code: str | None = "MISSING_KEY",
        **context: Any,
    ) -> None:
        message = message or f"Required configuration key missing: {key}"

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            key=key,
            **context,
        )


class ConfigEnvironmentError(ConfigError):
    """Raised when there's an issue with the environment configuration."""

    def __init__(
        self,
        message: str,
        environment: str | None = None,
        error_code: str | None = "ENVIRONMENT_ERROR",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if environment:
            ctx["environment"] = environment

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )


# =============================================================================
# Database Errors
# =============================================================================


class DBError(ComponentError):
    """Base class for all database-related errors."""

    PREFIX: str = "DB"
    CATEGORY: ErrorCategory = ErrorCategory.DB


class DBConnectionError(DBError):
    """Raised when a database connection fails."""

    def __init__(
        self,
        message: str = "Failed to connect to database",
        connection_string: str | None = None,
        error_code: str | None = "CONNECTION_ERROR",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if connection_string:
            # Sanitize connection string to remove credentials
            sanitized = self._sanitize_connection_string(connection_string)
            ctx["connection_string"] = sanitized

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )

    @staticmethod
    def _sanitize_connection_string(conn_str: str) -> str:
        """Sanitize a connection string to remove sensitive information."""
        # Basic implementation - in real code, this would be more sophisticated
        import re

        # Replace password in connection string
        return re.sub(
            r"password=([^;]*)", "password=***", conn_str, flags=re.IGNORECASE
        )


class DBQueryError(DBError):
    """Raised when a database query fails."""

    def __init__(
        self,
        message: str,
        query: str | None = None,
        params: dict[str, Any] | None = None,
        error_code: str | None = "QUERY_ERROR",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if query:
            ctx["query"] = query
        if params:
            # Sanitize params to avoid logging sensitive data
            ctx["params"] = {
                k: "***" if k.lower() in ["password", "secret", "token"] else v
                for k, v in params.items()
            }

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )


class DBMigrationError(DBError):
    """Raised when a database migration fails."""

    def __init__(
        self,
        message: str,
        migration_version: str | None = None,
        migration_name: str | None = None,
        error_code: str | None = "MIGRATION_ERROR",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if migration_version:
            ctx["migration_version"] = migration_version
        if migration_name:
            ctx["migration_name"] = migration_name

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )


class DBConstraintViolationError(DBError):
    """Raised when a database constraint is violated."""

    def __init__(
        self,
        message: str,
        constraint_name: str | None = None,
        table_name: str | None = None,
        error_code: str | None = "CONSTRAINT_VIOLATION",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if constraint_name:
            ctx["constraint_name"] = constraint_name
        if table_name:
            ctx["table_name"] = table_name

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )


class DBDeadlockError(DBError):
    """Raised when a database deadlock is detected."""

    def __init__(
        self,
        message: str = "Database deadlock detected",
        transaction_id: str | None = None,
        error_code: str | None = "DEADLOCK",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if transaction_id:
            ctx["transaction_id"] = transaction_id

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )


# =============================================================================
# Dependency Injection Errors
# =============================================================================


class DIError(ComponentError):
    """Base class for all dependency injection related errors."""

    PREFIX: str = "DI"
    CATEGORY: ErrorCategory = ErrorCategory.DI


class DIServiceNotRegisteredError(DIError):
    """Raised when a service is not registered in the container."""

    def __init__(
        self,
        service_type: str,
        message: str | None = None,
        error_code: str | None = "SERVICE_NOT_REGISTERED",
        **context: Any,
    ) -> None:
        message = message or f"Service not registered: {service_type}"

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            service_type=service_type,
            **context,
        )


class DICircularDependencyError(DIError):
    """Raised when a circular dependency is detected."""

    def __init__(
        self,
        dependency_chain: list[str],
        message: str | None = None,
        error_code: str | None = "CIRCULAR_DEPENDENCY",
        **context: Any,
    ) -> None:
        message = (
            message or f"Circular dependency detected: {' -> '.join(dependency_chain)}"
        )

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            dependency_chain=dependency_chain,
            **context,
        )


class DIServiceCreationError(DIError):
    """Raised when a service cannot be created."""

    def __init__(
        self,
        service_type: str,
        reason: str,
        message: str | None = None,
        error_code: str | None = "SERVICE_CREATION_ERROR",
        **context: Any,
    ) -> None:
        message = message or f"Failed to create service {service_type}: {reason}"

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            service_type=service_type,
            reason=reason,
            **context,
        )


class DIContainerDisposedError(DIError):
    """Raised when trying to use a disposed container."""

    def __init__(
        self,
        message: str = "Container has been disposed",
        error_code: str | None = "CONTAINER_DISPOSED",
        **context: Any,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            **context,
        )


class DIScopeDisposedError(DIError):
    """Raised when trying to use a disposed scope."""

    def __init__(
        self,
        message: str = "Scope has been disposed",
        scope_id: str | None = None,
        error_code: str | None = "SCOPE_DISPOSED",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if scope_id:
            ctx["scope_id"] = scope_id

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )


# =============================================================================
# Event System Errors
# =============================================================================


class EventError(ComponentError):
    """Base class for all event-related errors."""

    PREFIX: str = "EVENT"
    CATEGORY: ErrorCategory = ErrorCategory.EVENT


class EventPublishError(EventError):
    """Raised when publishing an event fails."""

    def __init__(
        self,
        event_type: str,
        reason: str,
        message: str | None = None,
        error_code: str | None = "PUBLISH_ERROR",
        **context: Any,
    ) -> None:
        message = message or f"Failed to publish event '{event_type}': {reason}"

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            event_type=event_type,
            reason=reason,
            **context,
        )


class EventHandlerError(EventError):
    """Raised when an event handler fails."""

    def __init__(
        self,
        event_type: str,
        handler_name: str,
        reason: str,
        message: str | None = None,
        error_code: str | None = "HANDLER_ERROR",
        **context: Any,
    ) -> None:
        message = (
            message
            or f"Event handler '{handler_name}' failed for event '{event_type}': {reason}"
        )

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            event_type=event_type,
            handler_name=handler_name,
            reason=reason,
            **context,
        )


class EventSerializationError(EventError):
    """Raised when event serialization fails."""

    def __init__(
        self,
        event_type: str,
        reason: str,
        message: str | None = None,
        error_code: str | None = "SERIALIZATION_ERROR",
        **context: Any,
    ) -> None:
        message = message or f"Failed to serialize event '{event_type}': {reason}"

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            event_type=event_type,
            reason=reason,
            **context,
        )


class EventDeserializationError(EventError):
    """Raised when event deserialization fails."""

    def __init__(
        self,
        event_type: str,
        reason: str,
        message: str | None = None,
        error_code: str | None = "DESERIALIZATION_ERROR",
        **context: Any,
    ) -> None:
        message = message or f"Failed to deserialize event '{event_type}': {reason}"

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            event_type=event_type,
            reason=reason,
            **context,
        )


class EventVersioningError(EventError):
    """Raised when there's an issue with event versioning."""

    def __init__(
        self,
        event_type: str,
        from_version: int,
        to_version: int,
        operation: str,
        reason: str,
        message: str | None = None,
        error_code: str | None = "VERSIONING_ERROR",
        **context: Any,
    ) -> None:
        message = (
            message
            or f"Failed to {operation} event '{event_type}' from v{from_version} to v{to_version}: {reason}"
        )

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            event_type=event_type,
            from_version=from_version,
            to_version=to_version,
            operation=operation,
            reason=reason,
            **context,
        )


# =============================================================================
# Security Errors
# =============================================================================


class SecurityError(ComponentError):
    """Base class for all security-related errors."""

    PREFIX: str = "SEC"
    CATEGORY: ErrorCategory = ErrorCategory.SECURITY


class AuthenticationError(SecurityError):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        username: str | None = None,
        error_code: str | None = "AUTH_FAILED",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if username:
            ctx["username"] = username

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )


class AuthorizationError(SecurityError):
    """Raised when authorization fails."""

    def __init__(
        self,
        message: str = "Authorization failed",
        username: str | None = None,
        resource: str | None = None,
        action: str | None = None,
        error_code: str | None = "AUTH_DENIED",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if username:
            ctx["username"] = username
        if resource:
            ctx["resource"] = resource
        if action:
            ctx["action"] = action

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )


class TokenError(SecurityError):
    """Raised when there's an issue with a security token."""

    def __init__(
        self,
        message: str,
        error_code: str | None = "TOKEN_ERROR",
        **context: Any,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            **context,
        )


class TokenExpiredError(TokenError):
    """Raised when a security token has expired."""

    def __init__(
        self,
        message: str = "Token has expired",
        expiry_time: str | None = None,
        error_code: str | None = "TOKEN_EXPIRED",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if expiry_time:
            ctx["expiry_time"] = expiry_time

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )


class TokenInvalidError(TokenError):
    """Raised when a security token is invalid."""

    def __init__(
        self,
        message: str = "Token is invalid",
        reason: str | None = None,
        error_code: str | None = "TOKEN_INVALID",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if reason:
            ctx["reason"] = reason

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )


# =============================================================================
# Validation Errors
# =============================================================================


class ValidationError(ComponentError):
    """Base class for all validation-related errors."""

    PREFIX: str = "VAL"
    CATEGORY: ErrorCategory = ErrorCategory.VALIDATION


class SchemaValidationError(ValidationError):
    """Raised when schema validation fails."""

    def __init__(
        self,
        message: str,
        schema_name: str | None = None,
        field_name: str | None = None,
        field_value: Any | None = None,
        error_code: str | None = "SCHEMA_ERROR",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if schema_name:
            ctx["schema_name"] = schema_name
        if field_name:
            ctx["field_name"] = field_name
        if field_value is not None:
            ctx["field_value"] = str(field_value)

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )


class InputValidationError(ValidationError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        field_name: str | None = None,
        field_value: Any | None = None,
        error_code: str | None = "INPUT_ERROR",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if field_name:
            ctx["field_name"] = field_name
        if field_value is not None:
            ctx["field_value"] = str(field_value)

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )


class BusinessRuleValidationError(ValidationError):
    """Raised when a business rule validation fails."""

    def __init__(
        self,
        message: str,
        rule_name: str | None = None,
        error_code: str | None = "BUSINESS_RULE_ERROR",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if rule_name:
            ctx["rule_name"] = rule_name

        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )
