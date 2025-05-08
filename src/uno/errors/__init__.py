# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Comprehensive error handling framework for the Uno application.

This module provides a unified approach to error handling with
structured errors, error codes, contextual information, and
integration with both exception-based and functional error handling.
"""

from uno.errors.base import (
    ErrorCategory,
    ErrorCode,
    ErrorInfo,
    ErrorSeverity,
    UnoError,
)

__all__ = [
    "ErrorCategory",
    "ErrorCode",
    "ErrorInfo",
    "ErrorSeverity",
    "UnoError",
]
