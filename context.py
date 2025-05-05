"""
Context objects for the event handling system.

This module provides the shared context objects that are passed between
components in the event handling system. It is separated from other modules
to avoid circular imports.
"""

from dataclasses import dataclass, field
from typing import Any, TypeVar, cast

from uno.core.events.events import DomainEvent

T = TypeVar("T", bound=DomainEvent)


@dataclass
class EventHandlerContext:
    """
    Context for event handlers with metadata and utilities.

    The context is passed to event handlers and provides access to:
    - The original event object
    - Metadata about the event (correlation ID, causation ID, etc.)
    - Extra data that can be used for passing state between middleware
    """

    event: DomainEvent
    metadata: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def get_typed_event(self, event_type: type[T]) -> T:
        """
        Get the event as a specific type.

        This is a convenience method for handlers that know the
        expected event type and want to avoid repetitive casting.

        Args:
            event_type: The expected event type

        Returns:
            The event cast to the specified type

        Raises:
            TypeError: If the event is not of the expected type
        """
        if not isinstance(self.event, event_type):
            raise TypeError(
                f"Expected event of type {event_type.__name__}, got {type(self.event).__name__}"
            )

        return cast("T", self.event)

    def with_extra(self, key: str, value: Any) -> "EventHandlerContext":
        """
        Return a new context with an extra value added.

        This is a convenience method for adding extra data to the context
        without mutating the original context.

        Args:
            key: The key for the extra data
            value: The value to add

        Returns:
            A new context with the extra data added
        """
        new_extra = self.extra.copy()
        new_extra[key] = value
        return EventHandlerContext(
            event=self.event, metadata=self.metadata.copy(), extra=new_extra
        )
