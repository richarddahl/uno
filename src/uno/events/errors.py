# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Error types specific to the events package.

This module defines custom exception types used throughout the event sourcing system.

NOTICE: Some error types have been moved to uno.persistence.event_sourcing.errors.
Consider using the error types there for new code.
"""

import warnings
from typing import Any

from uno.errors.base import UnoError

# Emit deprecation warning
warnings.warn(
    "Some error types in uno.events.errors are deprecated. "
    "Consider using uno.persistence.event_sourcing.errors for new code.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "EventErrorCode",
    "EventError",
    "EventHandlerError",
    "EventPublishError",
    "EventStoreError",
    "EventNotFoundError",
    "EventConflictError",
    "EventSubscribeError",
    "EventSerializationError",
    "EventDeserializationError",
    "EventReplayError",
    "EventVersioningError",
    "EventProcessingError",
    "EventCancellationError",
]

# -----------------------------------------------------------------------------
# Event error codes
# -----------------------------------------------------------------------------


class EventErrorCode:
    """Error codes for event system."""

    PUBLISH_ERROR = "EVENT-1001"
    SUBSCRIBE_ERROR = "EVENT-1002"
    HANDLER_ERROR = "EVENT-1003"
    SERIALIZATION_ERROR = "EVENT-1004"
    DESERIALIZATION_ERROR = "EVENT-1005"
    UPCAST_ERROR = "EVENT-1006"
    DOWNCAST_ERROR = "EVENT-1007"
    STORE_ERROR = "EVENT-1008"
    REPLAY_ERROR = "EVENT-1009"


# -----------------------------------------------------------------------------
# Event exceptions
# -----------------------------------------------------------------------------


class EventError(UnoError):
    """Base class for all event-related errors."""

    code = None


class EventStoreError(EventError):
    """Base class for event store errors."""

    code = EventErrorCode.STORE_ERROR


class EventNotFoundError(EventStoreError):
    """Error raised when an event is not found in the event store."""

    pass


class EventConflictError(EventStoreError):
    """Error raised when there's a conflict while saving events."""

    pass


# -----------------------------------------------------------------------------
# Event error classes
# -----------------------------------------------------------------------------


class EventPublishError(UnoError):
    """Raised when event publishing fails."""

    def __init__(self, event_type: str, reason: str, **context: Any):
        super().__init__(
            message=f"Failed to publish event '{event_type}': {reason}",
            code=EventErrorCode.PUBLISH_ERROR,
            event_type=event_type,
            reason=reason,
            **context,
        )


class EventSubscribeError(UnoError):
    """Raised when event subscription fails."""

    def __init__(self, event_type: str, reason: str, **context: Any):
        super().__init__(
            message=f"Failed to subscribe to event '{event_type}': {reason}",
            code=EventErrorCode.SUBSCRIBE_ERROR,
            event_type=event_type,
            reason=reason,
            **context,
        )


class EventHandlerError(UnoError):
    """Raised when an event handler fails."""

    def __init__(self, event_type: str, handler_name: str, reason: str, **context: Any):
        super().__init__(
            message=f"Handler '{handler_name}' failed for event '{event_type}': {reason}",
            code=EventErrorCode.HANDLER_ERROR,
            event_type=event_type,
            handler_name=handler_name,
            reason=reason,
            **context,
        )


class EventSerializationError(UnoError):
    """Raised when event serialization fails."""

    def __init__(self, event_type: str, reason: str, **context: Any):
        super().__init__(
            message=f"Failed to serialize event '{event_type}': {reason}",
            code=EventErrorCode.SERIALIZATION_ERROR,
            event_type=event_type,
            reason=reason,
            **context,
        )


class EventDeserializationError(UnoError):
    """Raised when event deserialization fails."""

    def __init__(self, event_type: str, reason: str, **context: Any):
        super().__init__(
            message=f"Failed to deserialize event '{event_type}': {reason}",
            code=EventErrorCode.DESERIALIZATION_ERROR,
            event_type=event_type,
            reason=reason,
            **context,
        )


class EventUpcastError(UnoError):
    """Raised when event upcasting fails."""

    def __init__(
        self,
        event_type: str,
        from_version: int,
        to_version: int,
        reason: str,
        **context: Any,
    ):
        super().__init__(
            message=f"Failed to upcast event '{event_type}' from v{from_version} to v{to_version}: {reason}",
            code=EventErrorCode.UPCAST_ERROR,
            event_type=event_type,
            from_version=from_version,
            to_version=to_version,
            reason=reason,
            **context,
        )


class EventDowncastError(UnoError):
    """Raised when event downcasting fails."""

    def __init__(
        self,
        event_type: str,
        from_version: int,
        to_version: int,
        reason: str,
        **context: Any,
    ):
        super().__init__(
            message=f"Failed to downcast event '{event_type}' from v{from_version} to v{to_version}: {reason}",
            code=EventErrorCode.DOWNCAST_ERROR,
            event_type=event_type,
            from_version=from_version,
            to_version=to_version,
            reason=reason,
            **context,
        )


class EventReplayError(UnoError):
    """Raised when event replay fails."""

    def __init__(self, event_type: str, reason: str, **context: Any):
        super().__init__(
            message=f"Failed to replay event '{event_type}': {reason}",
            code=EventErrorCode.REPLAY_ERROR,
            event_type=event_type,
            reason=reason,
            **context,
        )


class EventVersioningError(UnoError):
    """Raised when there's an issue with event versioning."""

    def __init__(
        self,
        event_type: str,
        from_version: int,
        to_version: int,
        operation: str,
        reason: str,
        message: str | None = None,
        **context: Any,
    ):
        message = (
            message
            or f"Failed to {operation} event '{event_type}' from v{from_version} to v{to_version}: {reason}"
        )

        super().__init__(
            message=message,
            code="EVENT-VERSION-ERROR",
            event_type=event_type,
            from_version=from_version,
            to_version=to_version,
            operation=operation,
            reason=reason,
            **context,
        )


class EventProcessingError(EventError):
    """
    Error when processing an event fails.

    This error is raised when processing an event with handlers fails.
    """

    def __init__(self, event: Any, reason: str) -> None:
        """
        Initialize the error.

        Args:
            event: The event that failed to process
            reason: The reason for the failure
        """
        self.event = event
        self.reason = reason
        message = f"Event processing failed for {getattr(event, 'event_type', type(event).__name__)}: {reason}"
        super().__init__(
            code=EventErrorCode.HANDLER_ERROR,
            message=message,
            details={
                "event_type": getattr(event, "event_type", type(event).__name__),
                "event_id": getattr(event, "event_id", None),
                "reason": reason,
            },
        )


class EventCancellationError(EventError):
    """
    Error when event processing is cancelled.

    This error is raised when event processing is cancelled explicitly
    before normal completion.
    """

    def __init__(self, event: Any) -> None:
        """
        Initialize the error.

        Args:
            event: The event whose processing was cancelled
        """
        self.event = event
        message = f"Event processing cancelled for {getattr(event, 'event_type', type(event).__name__)}"
        super().__init__(
            code=EventErrorCode.HANDLER_ERROR,
            message=message,
            details={
                "event_type": getattr(event, "event_type", type(event).__name__),
                "event_id": getattr(event, "event_id", None),
            },
        )


class CommandDispatchError(UnoError):
    """Raised when command dispatch fails."""

    def __init__(self, command_type: str, reason: str, command: Any, **context: Any):
        super().__init__(
            message=f"Failed to dispatch command '{command_type}': {reason}",
            code="COMMAND-DISPATCH-ERROR",
            command_type=command_type,
            reason=reason,
            command=command,
            **context,
        )


class SnapshotStoreError(UnoError):
    """Raised when snapshot storage/retrieval/deletion fails."""

    def __init__(
        self,
        operation: str,
        aggregate_id: str | None = None,
        original_exception: Exception | None = None,
        message: str | None = None,
        **context: Any,
    ):
        base_message = (
            message
            or f"Snapshot operation '{operation}' failed for aggregate {aggregate_id or '<unknown>'}"
        )
        super().__init__(
            message=base_message,
            code="SNAPSHOT-STORE-ERROR",
            operation=operation,
            aggregate_id=aggregate_id,
            original_exception=repr(original_exception) if original_exception else None,
            **context,
        )
