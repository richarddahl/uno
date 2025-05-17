# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework

"""
Error handling for the Uno framework.
"""

from __future__ import annotations
from typing import Any

from uno.errors.base import UnoError, ErrorCode, ErrorCategory, ErrorSeverity
from uno.errors.helpers import error_context_from_dict, wrap_exception

__all__ = [
    # Error categories
    "ErrorCode",
    "ErrorCategory",
    "ErrorSeverity",
    # Base errors
    "UnoError",
    # Error helpers
    "error_context_from_dict",
    "wrap_exception",  # Expose the helper function at the package level
]
