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
    AggregateNotDeletedError,
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

__all__ = [
    "AggregateNotDeletedError",
    "ErrorCategory",
    "ErrorCode",
    "ErrorContext",
    "ErrorInfo",
    "ErrorSeverity",
    "Failure",
    "FrameworkError",
    "LogConfig",
    "Result",
    "Success",
    "UnoNotImplementedError",
    "ValidationContext",
    "ValidationError",
    "add_error_context",
    "add_logging_context",
    "clear_logging_context",
    "combine",
    "combine_dict",
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
