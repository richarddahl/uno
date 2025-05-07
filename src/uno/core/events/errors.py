# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT

"""
Event system error definitions.
"""

from typing import Any

from uno.core.errors.base import FrameworkError

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
# Event error classes
# -----------------------------------------------------------------------------


class EventPublishError(FrameworkError):
    """Raised when event publishing fails."""

    def __init__(self, event_type: str, reason: str, **context: Any):
        super().__init__(
            message=f"Failed to publish event '{event_type}': {reason}",
            error_code=EventErrorCode.PUBLISH_ERROR,
            event_type=event_type,
            reason=reason,
            **context,
        )


class EventSubscribeError(FrameworkError):
    """Raised when event subscription fails."""

    def __init__(self, event_type: str, reason: str, **context: Any):
        super().__init__(
            message=f"Failed to subscribe to event '{event_type}': {reason}",
            error_code=EventErrorCode.SUBSCRIBE_ERROR,
            event_type=event_type,
            reason=reason,
            **context,
        )


class EventHandlerError(FrameworkError):
    """Raised when an event handler fails."""

    def __init__(self, event_type: str, handler_name: str, reason: str, **context: Any):
        super().__init__(
            message=f"Handler '{handler_name}' failed for event '{event_type}': {reason}",
            error_code=EventErrorCode.HANDLER_ERROR,
            event_type=event_type,
            handler_name=handler_name,
            reason=reason,
            **context,
        )


class EventSerializationError(FrameworkError):
    """Raised when event serialization fails."""

    def __init__(self, event_type: str, reason: str, **context: Any):
        super().__init__(
            message=f"Failed to serialize event '{event_type}': {reason}",
            error_code=EventErrorCode.SERIALIZATION_ERROR,
            event_type=event_type,
            reason=reason,
            **context,
        )


class EventDeserializationError(FrameworkError):
    """Raised when event deserialization fails."""

    def __init__(self, event_type: str, reason: str, **context: Any):
        super().__init__(
            message=f"Failed to deserialize event '{event_type}': {reason}",
            error_code=EventErrorCode.DESERIALIZATION_ERROR,
            event_type=event_type,
            reason=reason,
            **context,
        )


class EventUpcastError(FrameworkError):
    """Raised when event upcasting fails."""

    def __init__(self, event_type: str, from_version: int, to_version: int, reason: str, **context: Any):
        super().__init__(
            message=f"Failed to upcast event '{event_type}' from v{from_version} to v{to_version}: {reason}",
            error_code=EventErrorCode.UPCAST_ERROR,
            event_type=event_type,
            from_version=from_version,
            to_version=to_version,
            reason=reason,
            **context,
        )


class EventDowncastError(FrameworkError):
    """Raised when event downcasting fails."""

    def __init__(self, event_type: str, from_version: int, to_version: int, reason: str, **context: Any):
        super().__init__(
            message=f"Failed to downcast event '{event_type}' from v{from_version} to v{to_version}: {reason}",
            error_code=EventErrorCode.DOWNCAST_ERROR,
            event_type=event_type,
            from_version=from_version,
            to_version=to_version,
            reason=reason,
            **context,
        )


class EventStoreError(FrameworkError):
    """Raised when event storage fails."""

    def __init__(self, event_type: str, reason: str, **context: Any):
        super().__init__(
            message=f"Failed to store event '{event_type}': {reason}",
            error_code=EventErrorCode.STORE_ERROR,
            event_type=event_type,
            reason=reason,
            **context,
        )


class EventReplayError(FrameworkError):
    """Raised when event replay fails."""

    def __init__(self, event_type: str, reason: str, **context: Any):
        super().__init__(
            message=f"Failed to replay event '{event_type}': {reason}",
            error_code=EventErrorCode.REPLAY_ERROR,
            event_type=event_type,
            reason=reason,
            **context,
        ) 