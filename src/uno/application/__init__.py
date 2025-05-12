# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Application module for the Uno framework.
"""

from __future__ import annotations

from uno.application.errors import (
    APIAuthenticationError,
    APIAuthorizationError,
    APIError,
    APIRateLimitError,
    APIResourceNotFoundError,
    APIValidationError,
)

__all__ = [
    "APIError",
    "APIAuthenticationError",
    "APIAuthorizationError",
    "APIValidationError",
    "APIResourceNotFoundError",
    "APIRateLimitError",
]
