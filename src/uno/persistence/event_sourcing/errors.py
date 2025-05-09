# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Error types specific to the event sourcing persistence package.

This module defines custom exception types used throughout the event sourcing
persistence system.
"""

from uno.errors.base import UnoError


class EventPersistenceError(UnoError):
    """Base class for all event persistence related errors."""

    pass


class EventStoreError(EventPersistenceError):
    """Raised when an event store operation fails."""

    pass


class EventNotFoundError(EventPersistenceError):
    """Raised when an event cannot be found."""

    pass


class EventPublishError(EventPersistenceError):
    """Raised when an event fails to publish through a persistent bus."""

    pass


class OptimisticConcurrencyError(EventPersistenceError):
    """Raised when an optimistic concurrency check fails during event persistence."""

    pass
