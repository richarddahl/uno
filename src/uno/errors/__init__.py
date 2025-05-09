# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Public API for the Uno error handling system.

This module exports the public API for the Uno error handling system, including
the base error classes, utility functions, and common error patterns.
"""

from uno.errors.base import ErrorCategory, ErrorSeverity, UnoError
from uno.errors.helpers import (
    create_error,
    error_context_from_dict,
    wrap_exception as basic_wrap_exception,
)
from uno.errors.component_errors import (
    # Common base class
    ComponentError,
    # API errors
    APIError,
    APIAuthenticationError,
    APIAuthorizationError,
    APIValidationError,
    APIResourceNotFoundError,
    APIRateLimitError,
    # Configuration errors
    ConfigError,
    ConfigValidationError,
    ConfigFileNotFoundError,
    ConfigParseError,
    ConfigMissingKeyError,
    ConfigEnvironmentError,
    # Database errors
    DBError,
    DBConnectionError,
    DBQueryError,
    DBMigrationError,
    DBConstraintViolationError,
    DBDeadlockError,
    # Dependency Injection errors
    DIError,
    DIServiceNotRegisteredError,
    DICircularDependencyError,
    DIServiceCreationError,
    DIContainerDisposedError,
    DIScopeDisposedError,
    # Event errors
    EventError,
    EventPublishError,
    EventHandlerError,
    EventSerializationError,
    EventDeserializationError,
    EventVersioningError,
    # Security errors
    SecurityError,
    AuthenticationError,
    AuthorizationError,
    TokenError,
    TokenExpiredError,
    TokenInvalidError,
    # Validation errors
    ValidationError,
    SchemaValidationError,
    InputValidationError,
    BusinessRuleValidationError,
)

# Import factory functions
from uno.errors.factories import (
    # API error factories
    api_error,
    api_resource_not_found,
    api_validation_error,
    # Configuration error factories
    config_error,
    config_missing_key,
    config_file_not_found,
    # Database error factories
    db_error,
    db_connection_error,
    db_query_error,
    # Dependency Injection error factories
    di_error,
    di_service_not_registered,
    di_circular_dependency,
    # Event error factories
    event_error,
    event_publish_error,
    event_handler_error,
    # Security error factories
    security_error,
    authentication_error,
    authorization_error,
    # Validation error factories
    validation_error,
    schema_validation_error,
    input_validation_error,
)

# Import advanced exception wrapping
from uno.errors.wrap import (
    # Main wrapper function
    wrap_exception,
    # Domain-specific wrappers
    wrap_validation_exception,
    wrap_database_exception,
    wrap_api_exception,
    wrap_security_exception,
    wrap_event_exception,
    # Exception mapping utilities
    ExceptionMapping,
    with_error_context as with_exception_error_context,
    with_error_mapping,
    # Context extraction utilities
    default_context_extractor,
    default_message_formatter,
)

# Import error context enrichment
from uno.errors.context import (
    # Context management functions
    add_global_context,
    remove_global_context,
    get_global_context,
    clear_global_context,
    add_thread_context,
    remove_thread_context,
    get_thread_context,
    clear_thread_context,
    add_async_context,
    reset_async_context,
    remove_async_context,
    get_async_context,
    clear_async_context,
    get_current_context,
    enrich_error,
    # Context managers
    ErrorContext,
    # Decorators
    with_error_context,
    with_dynamic_error_context,
    capture_error_context,
    # Registries
    ContextRegistry,
    default_registry,
    # Bridge
    ErrorContextBridge,
    default_bridge,
    # Middleware
    ErrorContextMiddleware,
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
    # Core error types
    "UnoError",
    "ErrorCategory",
    "ErrorSeverity",
    # Helper functions
    "create_error",
    "basic_wrap_exception",
    "error_context_from_dict",
    # Component error base classes
    "ComponentError",
    # API errors
    "APIError",
    "APIAuthenticationError",
    "APIAuthorizationError",
    "APIValidationError",
    "APIResourceNotFoundError",
    "APIRateLimitError",
    # Configuration errors
    "ConfigError",
    "ConfigValidationError",
    "ConfigFileNotFoundError",
    "ConfigParseError",
    "ConfigMissingKeyError",
    "ConfigEnvironmentError",
    # Database errors
    "DBError",
    "DBConnectionError",
    "DBQueryError",
    "DBMigrationError",
    "DBConstraintViolationError",
    "DBDeadlockError",
    # Dependency Injection errors
    "DIError",
    "DIServiceNotRegisteredError",
    "DICircularDependencyError",
    "DIServiceCreationError",
    "DIContainerDisposedError",
    "DIScopeDisposedError",
    # Event errors
    "EventError",
    "EventPublishError",
    "EventHandlerError",
    "EventSerializationError",
    "EventDeserializationError",
    "EventVersioningError",
    # Security errors
    "SecurityError",
    "AuthenticationError",
    "AuthorizationError",
    "TokenError",
    "TokenExpiredError",
    "TokenInvalidError",
    # Validation errors
    "ValidationError",
    "SchemaValidationError",
    "InputValidationError",
    "BusinessRuleValidationError",
    # Factory functions
    "api_error",
    "api_resource_not_found",
    "api_validation_error",
    "config_error",
    "config_missing_key",
    "config_file_not_found",
    "db_error",
    "db_connection_error",
    "db_query_error",
    "di_error",
    "di_service_not_registered",
    "di_circular_dependency",
    "event_error",
    "event_publish_error",
    "event_handler_error",
    "security_error",
    "authentication_error",
    "authorization_error",
    "validation_error",
    "schema_validation_error",
    "input_validation_error",
    # Exception wrapping
    "wrap_exception",
    "wrap_validation_exception",
    "wrap_database_exception",
    "wrap_api_exception",
    "wrap_security_exception",
    "wrap_event_exception",
    "ExceptionMapping",
    "with_exception_error_context",
    "with_error_mapping",
    "default_context_extractor",
    "default_message_formatter",
    # Error context
    "add_global_context",
    "remove_global_context",
    "get_global_context",
    "clear_global_context",
    "add_thread_context",
    "remove_thread_context",
    "get_thread_context",
    "clear_thread_context",
    "add_async_context",
    "reset_async_context",
    "remove_async_context",
    "get_async_context",
    "clear_async_context",
    "get_current_context",
    "enrich_error",
    "ErrorContext",
    "with_error_context",
    "with_dynamic_error_context",
    "capture_error_context",
    "ContextRegistry",
    "default_registry",
    "ErrorContextBridge",
    "default_bridge",
    "ErrorContextMiddleware",
    # FastAPI middleware may not be available if FastAPI is not installed
    "FastAPIErrorContextMiddleware",
    "add_error_context_middleware",
]
