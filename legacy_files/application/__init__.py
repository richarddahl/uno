# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Application module for the Uno framework.
"""

from __future__ import annotations

from .errors import APPLICATION, APP_ERROR, APP_STARTUP, APP_SHUTDOWN, ApplicationError

__all__ = [
    "APPLICATION",
    "APP_ERROR",
    "APP_STARTUP",
    "APP_SHUTDOWN",
    "ApplicationError",
]
