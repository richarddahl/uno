"""
Event-related error classes for the Uno framework.

This module contains error classes that represent event-related exceptions.
"""

from typing import Any
from uno.errors.base import UnoError


class EventUpcastError(UnoError):
    """
    Raised when an event cannot be upcasted to the target version during event sourcing.
    This error indicates that no upcaster is registered or upcasting failed due to an internal error.
    """

    def __init__(
        self,
        event_type: str,
        from_version: int,
        to_version: int,
        message: str | None = None,
        **context: Any,
    ):
        message = message or (
            f"No upcaster registered for {event_type} v{from_version} -> v{to_version}"
        )
        super().__init__(
            message=message,
            error_code="CORE-1001",
            event_type=event_type,
            from_version=from_version,
            to_version=to_version,
            **context,
        )
