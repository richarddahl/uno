# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Error types specific to the projections package.

This module defines custom exception types used throughout the projections system.
"""

from uno.errors.base import UnoError


class ProjectionError(UnoError):
    """Base class for all projection-related errors."""

    pass


class ProjectionStoreError(ProjectionError):
    """Raised when a projection store operation fails."""

    pass


class ProjectionNotFoundError(ProjectionError):
    """Raised when a projection cannot be found."""

    pass
