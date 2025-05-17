# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
event_store.errors
Event store error definitions for Uno framework
"""

from __future__ import annotations

from typing import Any, Final

from uno.errors.base import ErrorCode, ErrorCategory, ErrorSeverity, UnoError

# Define error category and codes
EVENT_STORE = ErrorCategory.get_or_create("EVENT_STORE")
EVENT_STORE_ERROR: Final = ErrorCode.get_or_create("EVENT_STORE_ERROR", EVENT_STORE)
EVENT_STORE_APPEND_ERROR: Final = ErrorCode.get_or_create(
    "EVENT_STORE_APPEND_ERROR", EVENT_STORE
)
EVENT_STORE_GET_EVENTS_ERROR: Final = ErrorCode.get_or_create(
    "EVENT_STORE_GET_EVENTS_ERROR", EVENT_STORE
)
EVENT_STORE_SNAPSHOT_ERROR: Final = ErrorCode.get_or_create(
    "EVENT_STORE_SNAPSHOT_ERROR", EVENT_STORE
)
EVENT_STORE_VERSION_CONFLICT: Final = ErrorCode.get_or_create(
    "EVENT_STORE_VERSION_CONFLICT", EVENT_STORE
)
EVENT_STORE_REPLAY_ERROR: Final = ErrorCode.get_or_create(
    "EVENT_STORE_REPLAY_ERROR", EVENT_STORE
)
EVENT_STORE_CONNECT_ERROR: Final = ErrorCode.get_or_create(
    "EVENT_STORE_CONNECT_ERROR", EVENT_STORE
)
EVENT_STORE_TRANSACTION_ERROR: Final = ErrorCode.get_or_create(
    "EVENT_STORE_TRANSACTION_ERROR", EVENT_STORE
)
EVENT_STORE_SEARCH_ERROR: Final = ErrorCode.get_or_create(
    "EVENT_STORE_SEARCH_ERROR", EVENT_STORE
)


class EventStoreError(UnoError):
    """Base class for all event store-related errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = EVENT_STORE_ERROR,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize an event store error.

        Args:
            message: Human-readable error message
            code: Error code
            severity: How severe this error is
            context: Additional context information
            **kwargs: Additional context keys (will be merged with context)
        """
        if context is None:
            context = {}

        if kwargs:
            context.update(kwargs)

        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
        )

    def __str__(self) -> str:
        """Return a string representation of the error.

        Returns:
            String representation including severity, code, and message
        """
        return f"{self.severity}: {self.code}: {self.message}"


class EventStoreConnectionError(EventStoreError):
    """Error when there's an issue with the event store connection."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = EVENT_STORE_CONNECT_ERROR,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize an event store connection error.

        Args:
            message: Human-readable error message
            code: Error code (defaults to EVENT_STORE_CONNECT_ERROR)
            severity: How severe this error is
            context: Additional context information
            **kwargs: Additional context keys (will be merged with context)
        """
        super().__init__(
            message=message,
            code=code,
            severity=severity,
            context=context,
            **kwargs,
        )

    def __str__(self) -> str:
        """Return a string representation of the error."""
        if self.severity == ErrorSeverity.ERROR:
            return f"ERROR: {self.code}: {self.message}"
        return f"{self.severity}: {self.code}: {self.message}"


class EventStoreAppendError(EventStoreError):
    """Error when appending events to the event store."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = EVENT_STORE_APPEND_ERROR,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            **kwargs,
        )


class EventStoreGetEventsError(EventStoreError):
    """Error when retrieving events from the event store."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = EVENT_STORE_GET_EVENTS_ERROR,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            **kwargs,
        )


class EventStoreSnapshotError(EventStoreError):
    """Error related to snapshot operations."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = EVENT_STORE_SNAPSHOT_ERROR,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            **kwargs,
        )


class EventStoreVersionConflict(EventStoreError):
    """Error when there's a version conflict during append."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = EVENT_STORE_VERSION_CONFLICT,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            **kwargs,
        )


class EventStoreReplayError(EventStoreError):
    """Error when there's an issue during event replay."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = EVENT_STORE_REPLAY_ERROR,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            **kwargs,
        )


class EventStoreConnectError(EventStoreError):
    """Error when connecting to the event store."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = EVENT_STORE_CONNECT_ERROR,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            **kwargs,
        )


class EventStoreTransactionError(EventStoreError):
    """Error when there's an issue during a transaction."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = EVENT_STORE_TRANSACTION_ERROR,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            **kwargs,
        )


class EventStoreSearchError(EventStoreError):
    """Error when there's an issue during a search."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = EVENT_STORE_SEARCH_ERROR,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            **kwargs,
        )
