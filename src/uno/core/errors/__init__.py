# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Comprehensive error handling framework for the Uno application.

This module provides a unified approach to error handling with
structured errors, error codes, contextual information, and
integration with both exception-based and functional error handling.
"""

from uno.core.errors.base import (
    ErrorCategory,
    ErrorCode,
    ErrorContext,
    ErrorInfo,
    ErrorSeverity,
    FrameworkError,
    add_error_context,
    get_error_context,
    with_async_error_context,
    with_error_context,
)
from uno.core.errors.catalog import (
    ErrorCatalog,
    get_all_error_codes,
    get_error_code_info,
    register_error,
)
from uno.core.errors.definitions import (
    AggregateDeletedError,
    AggregateInvariantViolationError,
    AggregateNotDeletedError,
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
    DomainError,
    DomainValidationError,
    EntityNotFoundError,
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
    validate_fields,
)
from uno.core.errors.logging import (
    LogConfig,
    add_logging_context,
    clear_logging_context,
    configure_logging,
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

__all__ = [
    "AggregateDeletedError",
    "AggregateInvariantViolationError",
    "AggregateNotDeletedError",
    # Security
    "AuthenticationError",
    "AuthorizationError",
    "ComponentInitializationError",
    "ConcurrencyError",
    "ConfigInvalidError",
    "ConfigNotFoundError",
    "ConfigTypeMismatchError",
    # Core errors
    "CoreErrorCode",
    "DependencyCycleError",
    "DependencyNotFoundError",
    "DependencyResolutionError",
    "DeserializationError",
    # Base errors
    "DomainError",
    "DomainValidationError",
    "EntityNotFoundError",
    # Error catalog
    "ErrorCatalog",
    "ErrorCategory",
    "ErrorCode",
    "ErrorContext",
    "ErrorInfo",
    "ErrorSeverity",
    "Failure",
    "FieldValidationError",
    "FrameworkError",
    "InitializationError",
    "InterfaceMethodError",
    "InternalError",
    "LogConfig",
    "ObjectInvalidError",
    "ObjectNotFoundError",
    "ObjectPropertyError",
    "OperationFailedError",
    "ProtocolValidationError",
    # Result pattern
    "Result",
    "SerializationError",
    "Success",
    "UnoNotImplementedError",
    "ValidationContext",
    # Validation
    "ValidationError",
    "add_error_context",
    "add_logging_context",
    "clear_logging_context",
    "combine",
    "combine_dict",
    # Logging
    "configure_logging",
    "failure",
    "from_awaitable",
    "from_exception",
    "get_all_error_codes",
    "get_error_code_info",
    "get_error_context",
    "get_logging_context",
    "of",
    "register_error",
    "validate_fields",
    "with_async_error_context",
    "with_error_context",
    "with_logging_context",
]
