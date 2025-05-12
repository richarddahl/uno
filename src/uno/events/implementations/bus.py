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
        self.logger = logger
        self.config = config
        from uno.events.handlers import EventHandlerRegistry
        from uno.di.container import Container

        # Registry is now required for handler resolution
        self.registry = EventHandlerRegistry(logger, getattr(config, "container", None))

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
        Publish a domain event to all registered handlers (via DI-aware registry).

        Args:
            event: The domain event to publish
            metadata: Optional metadata to include with the event

        Raises:
            EventPublishError: If there's an error publishing the event
        """
        event_type = getattr(event, "event_type", type(event).__name__)
        try:
            await self.logger.info(
                "Publishing event",
                event_type=event_type,
                event=self._canonical_event_dict(event),
                metadata=metadata or {},
            )
            # Resolve handlers via DI-aware registry (async)
            handlers = await self.registry.resolve_handlers_for_event(event_type)
            if not handlers:
                await self.logger.debug(
                    "No handlers registered for event",
                    event_type=event_type,
                    event_id=getattr(event, "event_id", None),
                )
                return
            from uno.events.handlers import MiddlewareChainBuilder

            for handler in handlers:
                try:
                    chain = MiddlewareChainBuilder(handler, self.logger).build_chain(
                        self.registry._middleware
                    )
                    await chain(event)
                except Exception as exc:
                    await self.logger.error(
                        "Handler failed for event",
                        event_id=getattr(event, "event_id", None),
                        event_type=event_type,
                        handler=type(handler).__name__,
                        error=str(exc),
                        message=str(exc),
                        metadata=metadata,
                        exc_info=True,  # Only True, not the exception object
                    )
                    raise
        except Exception as exc:
            # Ensure all context values are serializable (stringify exception for logging)
            await self.logger.error(
                "Failed to publish event",
                event_type=event_type,
                error=str(exc),
                message=str(exc),
            )
            # Ensure the reason includes the original exception message
            raise EventPublishError(event_type=event_type, reason=str(exc)) from exc

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
