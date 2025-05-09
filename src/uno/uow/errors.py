# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Error types specific to the unit of work package.

This module defines custom exception types used throughout the unit of work system.
"""

from uno.errors.base import UnoError


class UnitOfWorkError(UnoError):
    """Base class for all unit of work related errors."""

    pass


class UnitOfWorkCommitError(UnitOfWorkError):
    """Raised when a unit of work fails to commit."""

    pass


class UnitOfWorkRollbackError(UnitOfWorkError):
    """Raised when a unit of work fails to roll back."""

    pass


class TransactionError(UnitOfWorkError):
    """Raised when a transaction operation fails."""

    pass
