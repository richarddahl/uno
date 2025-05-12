# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Error types specific to the event sourcing persistence package.

This module defines custom exception types used throughout the event sourcing
persistence system.
"""

from uno.errors.base import UnoError


from uno.errors.base import ErrorCategory, ErrorSeverity

class EventPersistenceError(UnoError):
    """Base class for all event persistence related errors."""
    def __init__(
        self,
        code: str,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict = None,
    ):
        super().__init__(
            code=code,
            message=message,
            category=ErrorCategory.EVENT,
            severity=severity,
            context=context or {},
        )

class EventStoreError(EventPersistenceError):
    """Raised when an event store operation fails."""
    def __init__(self, message: str, code: str = "EVENT_STORE_ERROR", severity: ErrorSeverity = ErrorSeverity.ERROR, context: dict = None):
        super().__init__(
            code=code,
            message=message,
            severity=severity,
            context=context or {},
        )

class EventNotFoundError(EventPersistenceError):
    """Raised when an event cannot be found."""
    def __init__(self, message: str, code: str = "EVENT_NOT_FOUND", severity: ErrorSeverity = ErrorSeverity.ERROR, context: dict = None):
        super().__init__(
            code=code,
            message=message,
            severity=severity,
            context=context or {},
        )

class EventPublishError(EventPersistenceError):
    """Raised when an event fails to publish through a persistent bus."""
    def __init__(self, message: str, code: str = "EVENT_PUBLISH_ERROR", severity: ErrorSeverity = ErrorSeverity.ERROR, context: dict = None):
        super().__init__(
            code=code,
            message=message,
            severity=severity,
            context=context or {},
        )

class OptimisticConcurrencyError(EventPersistenceError):
    """Raised when an optimistic concurrency check fails during event persistence."""
    def __init__(self, message: str, code: str = "OPTIMISTIC_CONCURRENCY_ERROR", severity: ErrorSeverity = ErrorSeverity.ERROR, context: dict = None):
        super().__init__(
            code=code,
            message=message,
            severity=severity,
            context=context or {},
        )

