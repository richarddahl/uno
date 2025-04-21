# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Comprehensive error handling framework for the Uno application.

This module provides a unified approach to error handling with
structured errors, error codes, contextual information, and
integration with both exception-based and functional error handling.
"""

from uno.core.errors.catalog import (
    ErrorCatalog,
    get_all_error_codes,
    get_error_code_info,
    register_error,
)
from uno.core.errors.definitions import (
    AggregateInvariantViolationError,
    AuthenticationError,
    AuthorizationError,
    ComponentInitializationError,
    ConcurrencyError,
    ConfigInvalidError,
    ConfigNotFoundError,
    ConfigTypeMismatchError,
    CoreErrorCode,
    DependencyCycleError,
    DependencyNotFoundError,
    DependencyResolutionError,
    DeserializationError,
    DomainValidationError,
    EntityNotFoundError,
    ErrorCategory,
    ErrorCode,
    ErrorContext,
    ErrorInfo,
    ErrorSeverity,
    FieldValidationError,
    InitializationError,
    InterfaceMethodError,
    InternalError,
    ObjectInvalidError,
    ObjectNotFoundError,
    ObjectPropertyError,
    OperationFailedError,
    ProtocolValidationError,
    SerializationError,
    ValidationContext,
    ValidationError,
    add_error_context,
    get_error_context,
    register_core_errors,
    validate_fields,
    with_async_error_context,
    with_error_context,
)
from uno.core.errors.logging import (
    LogConfig,
    add_logging_context,
    clear_logging_context,
    configure_logging,
    get_logger,
    get_logging_context,
    with_logging_context,
)
from uno.core.errors.result import (
    Failure,
    Result,
    Success,
    combine,
    combine_dict,
    failure,
    from_awaitable,
    from_exception,
    of,
)

# Register core errors
register_core_errors()

__all__ = [
    # Base errors
    "FrameworkError",
    "ErrorCode",
    "ErrorCategory",
    "ErrorSeverity",
    "ErrorContext",
    "ErrorInfo",
    "with_error_context",
    "with_async_error_context",
    "add_error_context",
    "get_error_context",
    "EntityNotFoundError",
    "ConcurrencyError",
    "DomainValidationError",
    "AggregateInvariantViolationError",
    # Error catalog
    "ErrorCatalog",
    "register_error",
    "get_error_code_info",
    "get_all_error_codes",
    # Result pattern
    "Result",
    "Success",
    "Failure",
    "of",
    "failure",
    "from_exception",
    "from_awaitable",
    "combine",
    "combine_dict",
    # Validation
    "ValidationError",
    "ValidationContext",
    "FieldValidationError",
    "validate_fields",
    # Logging
    "configure_logging",
    "get_logger",
    "LogConfig",
    "with_logging_context",
    "add_logging_context",
    "get_logging_context",
    "clear_logging_context",
    # Security
    "AuthenticationError",
    "AuthorizationError",
    # Core errors
    "CoreErrorCode",
    "ConfigNotFoundError",
    "ConfigInvalidError",
    "ConfigTypeMismatchError",
    "InitializationError",
    "ComponentInitializationError",
    "DependencyNotFoundError",
    "DependencyResolutionError",
    "DependencyCycleError",
    "ObjectNotFoundError",
    "ObjectInvalidError",
    "ObjectPropertyError",
    "SerializationError",
    "DeserializationError",
    "ProtocolValidationError",
    "InterfaceMethodError",
    "OperationFailedError",
    "UnoNotImplementedError",
    "InternalError",
]
