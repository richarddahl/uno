# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Error types specific to the events package.

This module defines custom exception types used throughout the event sourcing system.

NOTICE: Some error types have been moved to uno.persistence.event_sourcing.errors.
Consider using the error types there for new code.
"""

from __future__ import annotations

from typing import Any, Final

from uno.errors.base import ErrorCode, ErrorCategory, ErrorSeverity, UnoError

# Define event-specific error categories and codes
EVENT = ErrorCategory("EVENT")
EVENT_ERROR: Final = ErrorCode("EVENT_ERROR", EVENT)
EVENT_PUBLISH: Final = ErrorCode("EVENT_PUBLISH", EVENT)
EVENT_SUBSCRIBE: Final = ErrorCode("EVENT_SUBSCRIBE", EVENT)
EVENT_HANDLER: Final = ErrorCode("EVENT_HANDLER", EVENT)
EVENT_SERIALIZATION: Final = ErrorCode("EVENT_SERIALIZATION", EVENT)
EVENT_DESERIALIZATION: Final = ErrorCode("EVENT_DESERIALIZATION", EVENT)
EVENT_UPCAST: Final = ErrorCode("EVENT_UPCAST", EVENT)
EVENT_DOWNCAST: Final = ErrorCode("EVENT_DOWNCAST", EVENT)
EVENT_STORE: Final = ErrorCode("EVENT_STORE", EVENT)
EVENT_REPLAY: Final = ErrorCode("EVENT_REPLAY", EVENT)
EVENT_VERSIONING: Final = ErrorCode("EVENT_VERSIONING", EVENT)
EVENT_PROCESSING: Final = ErrorCode("EVENT_PROCESSING", EVENT)
EVENT_CANCELLATION: Final = ErrorCode("EVENT_CANCELLATION", EVENT)
SNAPSHOT_STORE: Final = ErrorCode("SNAPSHOT_STORE", EVENT)


class EventError(UnoError):
    """Base class for all event-related errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = EVENT_ERROR,
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


class EventStoreError(EventError):
    """Base class for event store errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = EVENT_STORE,
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


class EventNotFoundError(EventStoreError):
    """Error raised when an event is not found in the event store."""

    def __init__(
        self,
        message: str,
        event_id: str | None = None,
        code: ErrorCode = EVENT_STORE,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            event_id=event_id,
            **kwargs,
        )


class EventConflictError(EventStoreError):
    """Error raised when there's a conflict while saving events."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = EVENT_STORE,
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


class EventPublishError(EventError):
    """Raised when event publishing fails."""

    def __init__(
        self,
        event_type: str,
        reason: str,
        code: ErrorCode = EVENT_PUBLISH,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        message = f"Failed to publish event '{event_type}': {reason}"
        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            event_type=event_type,
            reason=reason,
            **kwargs,
        )


class EventSubscribeError(EventError):
    """Raised when event subscription fails."""

    def __init__(
        self,
        event_type: str,
        reason: str,
        code: ErrorCode = EVENT_SUBSCRIBE,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        message = f"Failed to subscribe to event '{event_type}': {reason}"
        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            event_type=event_type,
            reason=reason,
            **kwargs,
        )


class EventHandlerError(EventError):
    """Raised when an event handler fails."""

    def __init__(
        self,
        event_type: str,
        handler_name: str,
        reason: str,
        code: ErrorCode = EVENT_HANDLER,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        message = f"Handler '{handler_name}' failed for event '{event_type}': {reason}"
        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            event_type=event_type,
            handler_name=handler_name,
            reason=reason,
            **kwargs,
        )


class EventSerializationError(EventError):
    """Raised when event serialization fails."""

    def __init__(
        self,
        event_type: str,
        reason: str,
        code: ErrorCode = EVENT_SERIALIZATION,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        message = f"Failed to serialize event '{event_type}': {reason}"
        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            event_type=event_type,
            reason=reason,
            **kwargs,
        )


class EventDeserializationError(EventError):
    """Raised when event deserialization fails."""

    def __init__(
        self,
        event_type: str,
        reason: str,
        code: ErrorCode = EVENT_DESERIALIZATION,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        message = f"Failed to deserialize event '{event_type}': {reason}"
        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            event_type=event_type,
            reason=reason,
            **kwargs,
        )


class EventUpcastError(EventError):
    """Raised when event upcasting fails."""

    def __init__(
        self,
        event_type: str,
        from_version: int,
        to_version: int,
        reason: str,
        code: ErrorCode = EVENT_UPCAST,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        message = f"Failed to upcast event '{event_type}' from v{from_version} to v{to_version}: {reason}"
        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            event_type=event_type,
            from_version=from_version,
            to_version=to_version,
            reason=reason,
            **kwargs,
        )


class EventDowncastError(EventError):
    """Raised when event downcasting fails."""

    def __init__(
        self,
        event_type: str,
        from_version: int,
        to_version: int,
        reason: str,
        code: ErrorCode = EVENT_DOWNCAST,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        message = f"Failed to downcast event '{event_type}' from v{from_version} to v{to_version}: {reason}"
        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            event_type=event_type,
            from_version=from_version,
            to_version=to_version,
            reason=reason,
            **kwargs,
        )


class EventReplayError(EventError):
    """Raised when event replay fails."""

    def __init__(
        self,
        event_type: str,
        reason: str,
        code: ErrorCode = EVENT_REPLAY,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        message = f"Failed to replay event '{event_type}': {reason}"
        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            event_type=event_type,
            reason=reason,
            **kwargs,
        )


class EventVersioningError(EventError):
    """Raised when there's an issue with event versioning."""

    def __init__(
        self,
        event_type: str,
        from_version: int,
        to_version: int,
        operation: str,
        reason: str,
        message: str | None = None,
        code: ErrorCode = EVENT_VERSIONING,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        if message is None:
            message = f"Failed to {operation} event '{event_type}' from v{from_version} to v{to_version}: {reason}"

        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            event_type=event_type,
            from_version=from_version,
            to_version=to_version,
            operation=operation,
            reason=reason,
            **kwargs,
        )


class EventProcessingError(EventError):
    """Error when processing an event fails."""

    def __init__(
        self,
        event: Any,
        reason: str,
        code: ErrorCode = EVENT_PROCESSING,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        event_type = getattr(event, "event_type", type(event).__name__)
        event_id = getattr(event, "event_id", None)
        message = f"Event processing failed for {event_type}: {reason}"

        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            event_type=event_type,
            event_id=event_id,
            reason=reason,
            **kwargs,
        )


class EventCancellationError(EventError):
    """Error when event processing is cancelled."""

    def __init__(
        self,
        event: Any,
        code: ErrorCode = EVENT_CANCELLATION,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        event_type = getattr(event, "event_type", type(event).__name__)
        event_id = getattr(event, "event_id", None)
        message = f"Event processing cancelled for {event_type}"

        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            event_type=event_type,
            event_id=event_id,
            **kwargs,
        )


class SnapshotStoreError(EventError):
    """Raised when snapshot storage/retrieval/deletion fails."""

    def __init__(
        self,
        operation: str,
        aggregate_id: str | None = None,
        original_exception: Exception | None = None,
        message: str | None = None,
        code: ErrorCode = SNAPSHOT_STORE,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        if message is None:
            message = f"Snapshot operation '{operation}' failed for aggregate {aggregate_id or '<unknown>'}"

        exc_repr = repr(original_exception) if original_exception else None

        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            operation=operation,
            aggregate_id=aggregate_id,
            original_exception=exc_repr,
            **kwargs,
        )
