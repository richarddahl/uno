# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
events.errors
Event bus-specific error classes for the Uno framework
"""

from __future__ import annotations

from typing import Any, Final

from uno.errors.base import ErrorCode, ErrorCategory, ErrorSeverity, UnoError

# Define error category and codes
EVENT_BUS = ErrorCategory.get_or_create("EVENT_BUS")
EVENT_BUS_ERROR: Final = ErrorCode.get_or_create("EVENT_BUS_ERROR", EVENT_BUS)
EVENT_BUS_PUBLISH_ERROR: Final = ErrorCode.get_or_create(
    "EVENT_BUS_PUBLISH_ERROR", EVENT_BUS
)
EVENT_BUS_SUBSCRIBE_ERROR: Final = ErrorCode.get_or_create(
    "EVENT_BUS_SUBSCRIBE_ERROR", EVENT_BUS
)


class EventBusError(UnoError):
    """Base class for all event bus-related errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = EVENT_BUS_ERROR,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize an event bus error.

        Args:
            message: Human-readable error message
            code: Error code
            severity: How severe this error is
            context: Additional context information
            **kwargs: Additional context keys (will be merged with context)
        """
        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            **kwargs,
        )


class EventBusPublishError(EventBusError):

    def __init__(
        self,
        message: str,
        code: ErrorCode = EVENT_BUS_PUBLISH_ERROR,
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


class EventBusSubscribeError(EventBusError):

    def __init__(
        self,
        message: str,
        code: ErrorCode = EVENT_BUS_SUBSCRIBE_ERROR,
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
