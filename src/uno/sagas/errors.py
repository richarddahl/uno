# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Error types specific to the sagas package.

This module defines custom exception types used throughout the saga/process manager system.
"""

from uno.errors.base import UnoError


class SagaError(UnoError):
    """Base class for all saga-related errors."""

    pass


class SagaStoreError(SagaError):
    """Raised when a saga store operation fails."""

    pass


class SagaNotFoundError(SagaError):
    """Raised when a saga cannot be found."""

    pass


class SagaAlreadyExistsError(SagaError):
    """Raised when attempting to create a saga that already exists."""

    pass


class SagaCompensationError(SagaError):
    """Raised when saga compensation fails."""

    pass
