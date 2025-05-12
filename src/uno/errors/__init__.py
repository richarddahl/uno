# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Error handling for the Uno framework.
"""

from __future__ import annotations

from uno.errors.base import ErrorCategory, ErrorSeverity, UnoError
from uno.errors.helpers import create_error, error_context_from_dict, wrap_exception

__all__ = [
    # Error categories
    "ErrorCategory",
    "ErrorSeverity",
    # Base errors
    "UnoError",
    "MockIntegrationError",
    # Error helpers
    "create_error",
    "error_context_from_dict",
    "wrap_exception",
]


class MockIntegrationError(UnoError):
    """Test error class with additional attributes for integration testing."""

    def __init__(
        self,
        message: str,
        code: str,
        category: str = "integration",
        **kwargs: Any,
    ) -> None:
        """
        Initialize a new test integration error.

        Args:
            message: The error message
            code: Error code for categorization
            category: Error category string
            **kwargs: Additional context values
        """
        super().__init__(message=message, **kwargs)
        self.code = code
        self.category = category
        self.timestamp = datetime.datetime.now(datetime.UTC).isoformat()
