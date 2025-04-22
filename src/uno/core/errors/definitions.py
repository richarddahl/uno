# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT

"""
Consolidated error definitions for the Uno framework.

This module gathers all FrameworkError subclasses in one place,
removing duplication across core_errors.py, security.py, and validation.py.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from uno.core.errors.base import ErrorCategory, ErrorSeverity, FrameworkError
from uno.core.errors.catalog import register_error
from uno.core.errors.result import Failure, Success

# -----------------------------------------------------------------------------
# Core error codes
# -----------------------------------------------------------------------------


class CoreErrorCode:
    """Core framework error codes."""

    CONFIG_NOT_FOUND = "CORE-0001"
    CONFIG_INVALID = "CORE-0002"
    CONFIG_TYPE_MISMATCH = "CORE-0003"
    INIT_FAILED = "CORE-0101"
    COMPONENT_INIT_FAILED = "CORE-0102"
    DEPENDENCY_NOT_FOUND = "CORE-0201"
    DEPENDENCY_RESOLUTION_FAILED = "CORE-0202"
    DEPENDENCY_CYCLE = "CORE-0203"
    OBJECT_NOT_FOUND = "CORE-0301"
    OBJECT_INVALID = "CORE-0302"
    OBJECT_PROPERTY_ERROR = "CORE-0303"
    SERIALIZATION_ERROR = "CORE-0401"
    DESERIALIZATION_ERROR = "CORE-0402"
    PROTOCOL_VALIDATION_FAILED = "CORE-0501"
    INTERFACE_METHOD_MISSING = "CORE-0502"
    OPERATION_FAILED = "CORE-0901"
    NOT_IMPLEMENTED = "CORE-0902"
    INTERNAL_ERROR = "CORE-0903"


# -----------------------------------------------------------------------------
# Core error classes
# -----------------------------------------------------------------------------


class ConfigNotFoundError(FrameworkError):
    """Error raised when a configuration setting is not found."""

    def __init__(self, config_key: str, message: str | None = None, **context: Any):
        message = message or f"Configuration setting '{config_key}' not found"
        super().__init__(
            message=message,
            error_code=CoreErrorCode.CONFIG_NOT_FOUND,
            config_key=config_key,
            **context,
        )


class ConfigInvalidError(FrameworkError):
    """Error raised when a configuration setting is invalid."""

    def __init__(
        self, config_key: str, reason: str, message: str | None = None, **context: Any
    ):
        message = message or f"Invalid configuration setting '{config_key}': {reason}"
        super().__init__(
            message=message,
            error_code=CoreErrorCode.CONFIG_INVALID,
            config_key=config_key,
            reason=reason,
            **context,
        )


class ConfigTypeMismatchError(FrameworkError):
    """Error raised when a configuration setting has the wrong type."""

    def __init__(
        self,
        config_key: str,
        expected_type: str | type,
        actual_type: str | type,
        message: str | None = None,
        **context: Any,
    ):
        expected_type_str = (
            expected_type.__name__
            if isinstance(expected_type, type)
            else str(expected_type)
        )
        actual_type_str = (
            actual_type.__name__ if isinstance(actual_type, type) else str(actual_type)
        )
        message = (
            message
            or f"Configuration type mismatch for '{config_key}': expected {expected_type_str}, got {actual_type_str}"
        )
        super().__init__(
            message=message,
            error_code=CoreErrorCode.CONFIG_TYPE_MISMATCH,
            config_key=config_key,
            expected_type=expected_type_str,
            actual_type=actual_type_str,
            **context,
        )


class InitializationError(FrameworkError):
    """Error raised when framework initialization fails."""

    def __init__(
        self,
        reason: str,
        component: str | None = None,
        message: str | None = None,
        **context: Any,
    ):
        ctx = context.copy()
        if component:
            ctx["component"] = component
        message = message or f"Initialization failed: {reason}"
        register_error(
            message=message, error_code=CoreErrorCode.INIT_FAILED, reason=reason, **ctx
        )


class ComponentInitializationError(FrameworkError):
    """Error raised when a specific component fails to initialize."""

    def __init__(
        self, component: str, reason: str, message: str | None = None, **context: Any
    ):
        message = message or f"Component '{component}' initialization failed: {reason}"
        register_error(
            message=message,
            error_code=CoreErrorCode.COMPONENT_INIT_FAILED,
            component=component,
            reason=reason,
            **context,
        )


class DependencyNotFoundError(FrameworkError):
    """Error raised when a required dependency is not found."""

    def __init__(
        self,
        dependency_name: str,
        component: str | None = None,
        message: str | None = None,
        **context: Any,
    ):
        ctx = context.copy()
        if component:
            ctx["component"] = component
        message = message or f"Dependency '{dependency_name}' not found"
        register_error(
            message=message,
            error_code=CoreErrorCode.DEPENDENCY_NOT_FOUND,
            dependency_name=dependency_name,
            **ctx,
        )


class DependencyResolutionError(FrameworkError):
    """Error raised when dependency resolution fails."""

    def __init__(
        self,
        dependency_name: str,
        reason: str,
        message: str | None = None,
        **context: Any,
    ):
        message = (
            message or f"Failed to resolve dependency '{dependency_name}': {reason}"
        )
        super().__init__(
            message=message,
            error_code=CoreErrorCode.DEPENDENCY_RESOLUTION_FAILED,
            dependency_name=dependency_name,
            reason=reason,
            **context,
        )


class DependencyCycleError(FrameworkError):
    """Error raised when a dependency cycle is detected."""

    def __init__(
        self, cycle_components: list[str], message: str | None = None, **context: Any
    ):
        cycle_str = " -> ".join(cycle_components)
        message = message or f"Dependency cycle detected: {cycle_str}"
        super().__init__(
            message=message,
            error_code=CoreErrorCode.DEPENDENCY_CYCLE,
            cycle_components=cycle_components,
            **context,
        )


class ObjectNotFoundError(FrameworkError):
    """Error raised when an object is not found."""

    def __init__(
        self,
        object_type: str,
        object_id: str | None = None,
        message: str | None = None,
        **context: Any,
    ):
        ctx = context.copy()
        if object_id:
            ctx["object_id"] = object_id
        message = message or f"{object_type} not found"
        if object_id:
            message = f"{object_type} with ID '{object_id}' not found"
        super().__init__(
            message=message,
            error_code=CoreErrorCode.OBJECT_NOT_FOUND,
            object_type=object_type,
            **ctx,
        )


class ObjectInvalidError(FrameworkError):
    """Error raised when an object is invalid."""

    def __init__(
        self,
        object_type: str,
        reason: str,
        object_id: str | None = None,
        message: str | None = None,
        **context: Any,
    ):
        ctx = context.copy()
        if object_id:
            ctx["object_id"] = object_id
        message = message or f"Invalid {object_type}: {reason}"
        super().__init__(
            message=message,
            error_code=CoreErrorCode.OBJECT_INVALID,
            object_type=object_type,
            reason=reason,
            **ctx,
        )


class ObjectPropertyError(FrameworkError):
    """Error raised when there is an issue with an object property."""

    def __init__(
        self,
        object_type: str,
        property_name: str,
        reason: str,
        message: str | None = None,
        **context: Any,
    ):
        message = (
            message or f"Error with {object_type} property '{property_name}': {reason}"
        )
        super().__init__(
            message=message,
            error_code=CoreErrorCode.OBJECT_PROPERTY_ERROR,
            object_type=object_type,
            property_name=property_name,
            reason=reason,
            **context,
        )


class SerializationError(FrameworkError):
    """Error raised when object serialization fails."""

    def __init__(
        self, object_type: str, reason: str, message: str | None = None, **context: Any
    ):
        message = message or f"Failed to serialize {object_type}: {reason}"
        super().__init__(
            message=message,
            error_code=CoreErrorCode.SERIALIZATION_ERROR,
            object_type=object_type,
            reason=reason,
            **context,
        )


class DeserializationError(FrameworkError):
    """Error raised when object deserialization fails."""

    def __init__(
        self, object_type: str, reason: str, message: str | None = None, **context: Any
    ):
        message = message or f"Failed to deserialize {object_type}: {reason}"
        super().__init__(
            message=message,
            error_code=CoreErrorCode.DESERIALIZATION_ERROR,
            object_type=object_type,
            reason=reason,
            **context,
        )


class ProtocolValidationError(FrameworkError):
    """Error raised when protocol validation fails."""

    def __init__(
        self,
        protocol_name: str,
        reason: str,
        message: str | None = None,
        **context: Any,
    ):
        message = (
            message or f"Protocol validation failed for '{protocol_name}': {reason}"
        )
        super().__init__(
            message=message,
            error_code=CoreErrorCode.PROTOCOL_VALIDATION_FAILED,
            protocol_name=protocol_name,
            reason=reason,
            **context,
        )


class InterfaceMethodError(FrameworkError):
    """Error raised when a required interface method is missing."""

    def __init__(
        self,
        interface_name: str,
        method_name: str,
        message: str | None = None,
        **context: Any,
    ):
        message = (
            message
            or f"Required method '{method_name}' missing in interface '{interface_name}'"
        )
        super().__init__(
            message=message,
            error_code=CoreErrorCode.INTERFACE_METHOD_MISSING,
            interface_name=interface_name,
            method_name=method_name,
            **context,
        )


class OperationFailedError(FrameworkError):
    """Error raised when an operation fails."""

    def __init__(
        self, operation: str, reason: str, message: str | None = None, **context: Any
    ):
        message = message or f"Operation '{operation}' failed: {reason}"
        super().__init__(
            message=message,
            error_code=CoreErrorCode.OPERATION_FAILED,
            operation=operation,
            reason=reason,
            **context,
        )


class NotImplementedError(FrameworkError):
    """Error raised when a feature is not implemented."""

    def __init__(self, feature: str, message: str | None = None, **context: Any):
        message = message or f"Feature '{feature}' is not implemented"
        super().__init__(
            message=message,
            error_code=CoreErrorCode.NOT_IMPLEMENTED,
            feature=feature,
            **context,
        )


class InternalError(FrameworkError):
    """Error raised when an internal error occurs."""

    def __init__(self, reason: str, message: str | None = None, **context: Any):
        message = message or f"Internal error: {reason}"
        super().__init__(
            message=message,
            error_code=CoreErrorCode.INTERNAL_ERROR,
            reason=reason,
            **context,
        )


# -----------------------------------------------------------------------------
# Security errors
# -----------------------------------------------------------------------------


class AuthenticationError(FrameworkError):
    """Error when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: str = ErrorCategory.SECURITY.name,
        **context: Any,
    ):
        super().__init__(message, ErrorCategory.SECURITY.name, **context)


class AuthorizationError(FrameworkError):
    """Error when authorization fails."""

    def __init__(
        self,
        message: str = "Authorization failed",
        error_code: str = ErrorCategory.SECURITY.name,
        permission: str | None = None,
        resource: str | None = None,
        **context: Any,
    ):
        ctx = context.copy()
        if permission:
            ctx["permission"] = permission
        if resource:
            ctx["resource"] = resource
        super().__init__(message, error_code, **ctx)


# -----------------------------------------------------------------------------
# Domain Error Classes
# -----------------------------------------------------------------------------


class DomainError(FrameworkError):
    """
    Base class for all domain-level exceptions.

    Domain errors represent business rule violations and other exceptional
    conditions that arise in the domain model.
    """

    def __init__(
        self, message: str, code: str, details: dict[str, Any] | None = None, **kwargs
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        context = self.details.copy()
        if kwargs:
            context.update(kwargs)
        super().__init__(message=message, error_code=code, **context)

    def to_dict(self) -> dict[str, Any]:
        return {"message": self.message, "code": self.code, "details": self.details}


class DomainValidationError(DomainError):
    """
    Exception raised when domain validation fails.
    This exception is raised when an entity or value object fails validation,
    such as when a business rule is violated.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, "DOMAIN_VALIDATION_ERROR", details)


class EntityNotFoundError(DomainError):
    """
    Exception raised when an entity cannot be found.
    This exception is raised when attempting to retrieve an entity that doesn't exist in the repository.
    """

    def __init__(self, entity_type: str, entity_id: Any):
        message = f"{entity_type} with ID {entity_id} not found"
        details = {"entity_type": entity_type, "entity_id": str(entity_id)}
        super().__init__(message, "ENTITY_NOT_FOUND", details)


class BusinessRuleViolationError(DomainError):
    """
    Exception raised when a business rule is violated.
    This exception is raised when an operation would violate a business rule, such as when attempting to perform an action that is not allowed in the current state.
    """

    def __init__(
        self, message: str, rule_name: str, details: dict[str, Any] | None = None
    ):
        error_details = details or {}
        error_details["rule_name"] = rule_name
        super().__init__(message, "BUSINESS_RULE_VIOLATION", error_details)


class ConcurrencyError(DomainError):
    """
    Exception raised when a concurrency conflict occurs.
    This exception is raised when attempting to update an entity that has been modified by another operation since it was retrieved.
    """

    def __init__(self, entity_type: str, entity_id: Any):
        message = f"Concurrency conflict for {entity_type} with ID {entity_id}"
        details = {"entity_type": entity_type, "entity_id": str(entity_id)}
        super().__init__(message, "CONCURRENCY_CONFLICT", details)


class AggregateInvariantViolationError(DomainError):
    """
    Exception raised when an aggregate invariant is violated.
    This exception is raised when an operation would leave an aggregate in an invalid state, violating its invariants.
    """

    def __init__(self, aggregate_type: str, invariant_name: str, message: str):
        details = {"aggregate_type": aggregate_type, "invariant_name": invariant_name}
        super().__init__(message, "AGGREGATE_INVARIANT_VIOLATION", details)


class CommandHandlerNotFoundError(DomainError):
    """
    Exception raised when a command handler cannot be found.
    This exception is raised when attempting to dispatch a command for which there is no registered handler.
    """

    def __init__(self, command_type: str):
        message = f"No handler registered for command {command_type}"
        details = {"command_type": command_type}
        super().__init__(message, "COMMAND_HANDLER_NOT_FOUND", details)


class QueryHandlerNotFoundError(DomainError):
    """
    Exception raised when a query handler cannot be found.
    This exception is raised when attempting to dispatch a query for which there is no registered handler.
    """

    def __init__(self, query_type: str):
        message = f"No handler registered for query {query_type}"
        details = {"query_type": query_type}
        super().__init__(message, "QUERY_HANDLER_NOT_FOUND", details)


class CommandExecutionError(DomainError):
    """
    Exception raised when a command execution fails.
    This exception is raised when a command fails to execute due to an error in the command handler.
    """

    def __init__(
        self, command_type: str, message: str, details: dict[str, Any] | None = None
    ):
        error_details = details or {}
        error_details["command_type"] = command_type
        super().__init__(message, "COMMAND_EXECUTION_ERROR", error_details)


class QueryExecutionError(DomainError):
    """
    Exception raised when a query execution fails.
    This exception is raised when a query fails to execute due to an error in the query handler.
    """

    def __init__(
        self, query_type: str, message: str, details: dict[str, Any] | None = None
    ):
        error_details = details or {}
        error_details["query_type"] = query_type
        super().__init__(message, "QUERY_EXECUTION_ERROR", error_details)


class AuthorizationError(DomainError):
    """
    Exception raised when authorization fails.
    This exception is raised when a user is not authorized to perform an operation.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, "AUTHORIZATION_ERROR", details)


# -----------------------------------------------------------------------------
# Validation errors
# -----------------------------------------------------------------------------


@dataclass
class FieldValidationError:
    field: str
    message: str
    error_code: str
    value: Any = None


class ValidationContext:
    """Context for collecting field validation errors."""

    def __init__(self):
        self.errors = []

    def add_error(self, field: str, message: str, error_code: str, value: Any = None):
        self.errors.append(FieldValidationError(field, message, error_code, value))

    def has_errors(self):
        return len(self.errors) > 0


class ValidationError(FrameworkError):
    """Error raised when validation fails."""

    def __init__(
        self,
        validation_context: "ValidationContext",
        message: str | None = None,
        **context: Any,
    ):
        message = message or "Validation failed"
        # Only pass message and error_code to FrameworkError, not to Exception
        super().__init__(
            message,
            ErrorCategory.VALIDATION.name,
            validation_context=validation_context,
            **context,
        )


def validate_fields(
    data: dict[str, Any],
    required_fields: set[str] | None = None,
    validators: dict[str, list[Callable[[Any], str | None]]] | None = None,
    entity_name: str = "entity",
) -> "Success[None] | Failure[ValidationError]":
    """
    Validate fields in a dictionary.

    Instead of raising ValidationError, returns Failure(ValidationError) if errors are found, otherwise Success(None).

    Args:
        data: Dictionary of field values to validate.
        required_fields: Set of required field names.
        validators: Dict mapping field names to lists of validator functions.
        entity_name: Name of the entity for error messages.

    Returns:
        Success(None) if validation passes, or Failure(ValidationError) if errors are found.
    """
    validation_context = ValidationContext()
    if required_fields:
        for field in required_fields:
            if field not in data:
                validation_context.add_error(
                    field,
                    f"{entity_name} is missing required field '{field}'",
                    ErrorCategory.VALIDATION.name,
                )
    if validators:
        for field, validator_list in validators.items():
            for validator in validator_list:
                error_message = validator(data.get(field))
                if error_message:
                    validation_context.add_error(
                        field,
                        error_message,
                        ErrorCategory.VALIDATION.name,
                        data.get(field),
                    )
    if validation_context.has_errors():
        return Failure(ValidationError(validation_context))
    return Success(None)


# -----------------------------------------------------------------------------
# Register core error codes in the catalog
# -----------------------------------------------------------------------------

register_error(
    code=CoreErrorCode.CONFIG_NOT_FOUND,
    message_template="Configuration setting '{config_key}' not found",
    category=ErrorCategory.VALIDATION,
    severity=ErrorSeverity.ERROR,
    description="Missing config",
    http_status_code=400,
    retry_allowed=False,
)
register_error(
    code=CoreErrorCode.CONFIG_INVALID,
    message_template="Invalid configuration setting '{config_key}': {reason}",
    category=ErrorCategory.VALIDATION,
    severity=ErrorSeverity.ERROR,
    description="Invalid config",
    http_status_code=400,
    retry_allowed=False,
)
register_error(
    code=CoreErrorCode.CONFIG_TYPE_MISMATCH,
    message_template="Configuration type mismatch for '{config_key}': expected {expected_type}, got {actual_type}",
    category=ErrorCategory.VALIDATION,
    severity=ErrorSeverity.ERROR,
    description="Config type mismatch",
    http_status_code=400,
    retry_allowed=False,
)
register_error(
    code=CoreErrorCode.INIT_FAILED,
    message_template="Initialization failed: {reason}",
    category=ErrorCategory.SYSTEM,
    severity=ErrorSeverity.ERROR,
    description="Initialization failed",
    http_status_code=500,
    retry_allowed=False,
)
register_error(
    code=CoreErrorCode.COMPONENT_INIT_FAILED,
    message_template="Component '{component}' initialization failed: {reason}",
    category=ErrorCategory.SYSTEM,
    severity=ErrorSeverity.ERROR,
    description="Component initialization failed",
    http_status_code=500,
    retry_allowed=False,
)
register_error(
    code=CoreErrorCode.DEPENDENCY_NOT_FOUND,
    message_template="Dependency '{dependency_name}' not found",
    category=ErrorCategory.SYSTEM,
    severity=ErrorSeverity.ERROR,
    description="Dependency not found",
    http_status_code=500,
    retry_allowed=False,
)
register_error(
    code=CoreErrorCode.DEPENDENCY_RESOLUTION_FAILED,
    message_template="Failed to resolve dependency '{dependency_name}': {reason}",
    category=ErrorCategory.SYSTEM,
    severity=ErrorSeverity.ERROR,
    description="Dependency resolution failed",
    http_status_code=500,
    retry_allowed=False,
)
register_error(
    code=CoreErrorCode.DEPENDENCY_CYCLE,
    message_template="Dependency cycle detected: {cycle_components}",
    category=ErrorCategory.SYSTEM,
    severity=ErrorSeverity.ERROR,
    description="Dependency cycle detected",
    http_status_code=500,
    retry_allowed=False,
)
register_error(
    code=CoreErrorCode.OBJECT_NOT_FOUND,
    message_template="{object_type} not found",
    category=ErrorCategory.VALIDATION,
    severity=ErrorSeverity.ERROR,
    description="Object not found",
    http_status_code=404,
    retry_allowed=False,
)
register_error(
    code=CoreErrorCode.OBJECT_INVALID,
    message_template="Invalid {object_type}: {reason}",
    category=ErrorCategory.VALIDATION,
    severity=ErrorSeverity.ERROR,
    description="Invalid object",
    http_status_code=400,
    retry_allowed=False,
)
register_error(
    code=CoreErrorCode.OBJECT_PROPERTY_ERROR,
    message_template="Error with {object_type} property '{property_name}': {reason}",
    category=ErrorCategory.VALIDATION,
    severity=ErrorSeverity.ERROR,
    description="Object property error",
    http_status_code=400,
    retry_allowed=False,
)
register_error(
    code=CoreErrorCode.SERIALIZATION_ERROR,
    message_template="Failed to serialize {object_type}: {reason}",
    category=ErrorCategory.SYSTEM,
    severity=ErrorSeverity.ERROR,
    description="Serialization failed",
    http_status_code=500,
    retry_allowed=False,
)
register_error(
    code=CoreErrorCode.DESERIALIZATION_ERROR,
    message_template="Failed to deserialize {object_type}: {reason}",
    category=ErrorCategory.SYSTEM,
    severity=ErrorSeverity.ERROR,
    description="Deserialization failed",
    http_status_code=500,
    retry_allowed=False,
)
register_error(
    code=CoreErrorCode.PROTOCOL_VALIDATION_FAILED,
    message_template="Protocol validation failed for '{protocol_name}': {reason}",
    category=ErrorCategory.VALIDATION,
    severity=ErrorSeverity.ERROR,
    description="Protocol validation failed",
    http_status_code=400,
    retry_allowed=False,
)
register_error(
    code=CoreErrorCode.INTERFACE_METHOD_MISSING,
    message_template="Required method '{method_name}' missing in interface '{interface_name}'",
    category=ErrorCategory.VALIDATION,
    severity=ErrorSeverity.ERROR,
    description="Interface method missing",
    http_status_code=400,
    retry_allowed=False,
)
register_error(
    code=CoreErrorCode.OPERATION_FAILED,
    message_template="Operation '{operation}' failed: {reason}",
    category=ErrorCategory.SYSTEM,
    severity=ErrorSeverity.ERROR,
    description="Operation failed",
    http_status_code=500,
    retry_allowed=False,
)
register_error(
    code=CoreErrorCode.NOT_IMPLEMENTED,
    message_template="Feature '{feature}' is not implemented",
    category=ErrorCategory.SYSTEM,
    severity=ErrorSeverity.ERROR,
    description="Not implemented",
    http_status_code=501,
    retry_allowed=False,
)
register_error(
    code=CoreErrorCode.INTERNAL_ERROR,
    message_template="Internal error: {reason}",
    category=ErrorCategory.SYSTEM,
    severity=ErrorSeverity.ERROR,
    description="Internal error",
    http_status_code=500,
    retry_allowed=False,
)
