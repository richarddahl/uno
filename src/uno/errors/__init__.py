# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Public API for the Uno error handling system.

This module exports the public API for the Uno error handling system, including
the base error classes, utility functions, and common error patterns.
"""

from uno.errors.base import ErrorCategory, ErrorSeverity, UnoError

from uno.errors.helpers import create_error, error_context_from_dict, wrap_exception

__all__ = [
    # Core error types
    "UnoError",
    "ErrorCategory",
    "ErrorSeverity",
    # Helper functions
    "create_error",
    "wrap_exception",
    "error_context_from_dict",
]
