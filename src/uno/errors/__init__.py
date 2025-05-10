# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Public API for the Uno error handling system.

This module exports the public API for the Uno error handling system, including
the base error classes, utility functions, and common error patterns.
"""

from uno.errors.base import ErrorCategory, ErrorSeverity, UnoError
from uno.errors.component_errors import (
    APIAuthenticationError,
    APIAuthorizationError,
    # API errors
    APIError,
    APIRateLimitError,
    APIResourceNotFoundError,
    APIValidationError,
    AuthenticationError,
    AuthorizationError,
    BusinessRuleValidationError,
    # Common base class
    ComponentError,
    ConfigEnvironmentError,
    # Configuration errors
    ConfigError,
    ConfigFileNotFoundError,
    ConfigMissingKeyError,
    ConfigParseError,
    ConfigValidationError,
    ContainerDisposedError,
    DBConnectionError,
    DBConstraintViolationError,
    DBDeadlockError,
    # Database errors
    DBError,
    DBMigrationError,
    DBQueryError,
    DICircularDependencyError,
    # Dependency Injection errors
    DIError,
    DIScopeDisposedError,
    DIServiceCreationError,
    DIServiceNotRegisteredError,
    EventDeserializationError,
    # Event errors
    EventError,
    EventHandlerError,
    EventPublishError,
    EventSerializationError,
    EventVersioningError,
    InputValidationError,
    SchemaValidationError,
    # Security errors
    SecurityError,
    TokenError,
    TokenExpiredError,
    TokenInvalidError,
    # Validation errors
    ValidationError,
)

# Import error context enrichment
from uno.errors.context import (
    # Registries
    ContextRegistry,
    # Context managers
    ErrorContext,
    # Bridge
    ErrorContextBridge,
    # Middleware
    ErrorContextMiddleware,
    add_async_context,
    # Context management functions
    add_global_context,
    add_thread_context,
    capture_error_context,
    clear_async_context,
    clear_global_context,
    clear_thread_context,
    default_bridge,
    default_registry,
    enrich_error,
    get_async_context,
    get_current_context,
    get_global_context,
    get_thread_context,
    remove_async_context,
    remove_global_context,
    remove_thread_context,
    reset_async_context,
    with_dynamic_error_context,
    # Decorators
    with_error_context,
)

# Import factory functions
from uno.errors.factories import (
    # API error factories
    api_error,
    api_resource_not_found,
    api_validation_error,
    authentication_error,
    authorization_error,
    # Configuration error factories
    config_error,
    config_file_not_found,
    config_missing_key,
    db_connection_error,
    # Database error factories
    db_error,
    db_query_error,
    di_circular_dependency,
    # Dependency Injection error factories
    di_error,
    di_service_not_registered,
    # Event error factories
    event_error,
    event_handler_error,
    event_publish_error,
    input_validation_error,
    schema_validation_error,
    # Security error factories
    security_error,
    # Validation error factories
    validation_error,
)
from uno.errors.helpers import (
    create_error,
    error_context_from_dict,
    wrap_exception as basic_wrap_exception,
)

# Import advanced exception wrapping
from uno.errors.wrap import (
    # Exception mapping utilities
    ExceptionMapping,
    # Context extraction utilities
    default_context_extractor,
    default_message_formatter,
    with_error_context as with_exception_error_context,
    with_error_mapping,
    wrap_api_exception,
    wrap_database_exception,
    wrap_event_exception,
    # Main wrapper function
    wrap_exception,
    wrap_security_exception,
    # Domain-specific wrappers
    wrap_validation_exception,
)

# Import FastAPI middleware
try:
    from uno.errors.fastapi import (
        FastAPIErrorContextMiddleware,
        add_error_context_middleware,
    )
except ImportError:
    # FastAPI not installed, these won't be available
    pass

__all__ = [
    "APIAuthenticationError",
    "APIAuthorizationError",
    # API errors
    "APIError",
    "APIRateLimitError",
    "APIResourceNotFoundError",
    "APIValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "BusinessRuleValidationError",
    # Component error base classes
    "ComponentError",
    "ConfigEnvironmentError",
    # Configuration errors
    "ConfigError",
    "ConfigFileNotFoundError",
    "ConfigMissingKeyError",
    "ConfigParseError",
    "ConfigValidationError",
    "ContainerDisposedError",
    "ContextRegistry",
    "DBConnectionError",
    "DBConstraintViolationError",
    "DBDeadlockError",
    # Database errors
    "DBError",
    "DBMigrationError",
    "DBQueryError",
    "DICircularDependencyError",
    # Dependency Injection errors
    "DIError",
    "DIScopeDisposedError",
    "DIServiceCreationError",
    "DIServiceNotRegisteredError",
    "ErrorCategory",
    "ErrorContext",
    "ErrorContextBridge",
    "ErrorContextMiddleware",
    "ErrorSeverity",
    "EventDeserializationError",
    # Event errors
    "EventError",
    "EventHandlerError",
    "EventPublishError",
    "EventSerializationError",
    "EventVersioningError",
    "ExceptionMapping",
    # FastAPI middleware may not be available if FastAPI is not installed
    "FastAPIErrorContextMiddleware",
    "InputValidationError",
    "SchemaValidationError",
    # Security errors
    "SecurityError",
    "TokenError",
    "TokenExpiredError",
    "TokenInvalidError",
    # Core error types
    "UnoError",
    # Validation errors
    "ValidationError",
    "add_async_context",
    "add_error_context_middleware",
    # Error context
    "add_global_context",
    "add_thread_context",
    # Factory functions
    "api_error",
    "api_resource_not_found",
    "api_validation_error",
    "authentication_error",
    "authorization_error",
    "basic_wrap_exception",
    "capture_error_context",
    "clear_async_context",
    "clear_global_context",
    "clear_thread_context",
    "config_error",
    "config_file_not_found",
    "config_missing_key",
    # Helper functions
    "create_error",
    "db_connection_error",
    "db_error",
    "db_query_error",
    "default_bridge",
    "default_context_extractor",
    "default_message_formatter",
    "default_registry",
    "di_circular_dependency",
    "di_error",
    "di_service_not_registered",
    "enrich_error",
    "error_context_from_dict",
    "event_error",
    "event_handler_error",
    "event_publish_error",
    "get_async_context",
    "get_current_context",
    "get_global_context",
    "get_thread_context",
    "input_validation_error",
    "remove_async_context",
    "remove_global_context",
    "remove_thread_context",
    "reset_async_context",
    "schema_validation_error",
    "security_error",
    "validation_error",
    "with_dynamic_error_context",
    "with_error_context",
    "with_error_mapping",
    "with_exception_error_context",
    "wrap_api_exception",
    "wrap_database_exception",
    "wrap_event_exception",
    # Exception wrapping
    "wrap_exception",
    "wrap_security_exception",
    "wrap_validation_exception",
]
