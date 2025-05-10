# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
In-memory event bus implementation.

This module provides an in-memory implementation of the event bus for testing
and simple applications.
"""

from __future__ import annotations

from typing import Any, TypeVar, TYPE_CHECKING

from uno.events.base_event import DomainEvent
from uno.events.errors import EventHandlerError, EventPublishError

if TYPE_CHECKING:
    from uno.events.config import EventsConfig
    from uno.logging.protocols import LoggerProtocol

E = TypeVar("E", bound=DomainEvent)


class InMemoryEventBus:
    """
    Simple in-memory event bus for Uno event sourcing (development/testing).

    Canonical Serialization Contract:
        - All events published/logged MUST use `model_dump(exclude_none=True, exclude_unset=True, by_alias=True)` for serialization, storage, and transport.
        - This contract is enforced by logging the canonical dict form of each event.

    Error Handling:
        - Uses structured exception-based error handling
        - Errors are logged using structured logging

    Type Parameters:
        - E: DomainEvent (or subclass)
    """

    def __init__(self, logger: "LoggerProtocol", config: "EventsConfig") -> None:
        """
        Initialize the in-memory event bus.

        Args:
            logger: Logger instance for structured logging
            config: Events configuration settings
        """
        self._subscribers: dict[str, list[Any]] = {}
        self.logger = logger
        self.config = config

    def _canonical_event_dict(self, event: E) -> dict[str, Any]:
        """
        Canonical event serialization for logging, storage, and transport.

        Args:
            event: The domain event to serialize
        Returns:
            Canonical dict representation of the event
        """
        if hasattr(event, "model_dump"):
            return dict(
                event.model_dump(exclude_none=True, exclude_unset=True, by_alias=True)
            )
        elif hasattr(event, "to_dict"):
            return event.to_dict()
        return dict(event.__dict__)

    def subscribe(self, event_type: str, handler_func: Any) -> None:
        """
        Subscribe to a specific event type.

        Args:
            event_type: The type of event to subscribe to
            handler_func: The handler function to call when an event occurs
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler_func)

    async def publish(self, event: E, metadata: dict[str, Any] | None = None) -> None:
        """
        Publish a domain event to all subscribers.

        Args:
            event: The domain event to publish
            metadata: Optional metadata to include with the event

        Raises:
            EventPublishError: If there's an error publishing the event
        """
        event_type = getattr(event, "event_type", type(event).__name__)
        try:
            self.logger.info(
                "Publishing event",
                event_type=event_type,
                event=self._canonical_event_dict(event),
                metadata=metadata or {},
            )

            # Check if anyone is subscribed to this event type
            if event_type in self._subscribers:
                handlers = self._subscribers[event_type]
                for handler in handlers:
                    try:
                        await handler(event)
                    except Exception as e:
                        self.logger.error(
                            "Event handler error",
                            event_type=event_type,
                            handler=handler.__qualname__,
                            error=str(e),
                        )
                        # Don't reraise, continue with other handlers
                        if (
                            hasattr(self.config, "continue_on_handler_error")
                            and not self.config.continue_on_handler_error
                        ):
                            raise EventHandlerError(
                                event_type=event_type,
                                handler_name=handler.__qualname__,
                                reason=str(e),
                            ) from e
        except Exception as e:
            self.logger.error(
                "Failed to publish event",
                event_type=event_type,
                error=str(e),
            )
            raise EventPublishError(event_type=event_type, reason=str(e)) from e

    async def publish_many(self, events: list[E]) -> None:
        """
        Publish multiple domain events.

        Args:
            events: List of events to publish

        Raises:
            EventPublishError: If there's an error publishing any event
        """
        for event in events:
            await self.publish(event)
