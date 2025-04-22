# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT

from collections.abc import Callable
from typing import Protocol

from uno.core.domain.core import DomainEvent


class IEventBus(Protocol):
    """
    Abstraction for an event bus that publishes and subscribes to domain events.
    """

    def publish(self, event: DomainEvent) -> None:
        """Publish a domain event to the bus."""
        ...

    def subscribe(
        self, event_type: str, handler: Callable[[DomainEvent], None]
    ) -> None:
        """Subscribe a handler for a specific event_type."""
        ...


class InMemoryEventBus:
    """
    Simple in-memory bus for local testing and development.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[DomainEvent], None]]] = {}

    def subscribe(
        self, event_type: str, handler: Callable[[DomainEvent], None]
    ) -> None:
        """
        Register a handler function for a given event_type.
        """
        self._handlers.setdefault(event_type, []).append(handler)

    def publish(self, event: DomainEvent) -> None:
        """
        Dispatch an event to all subscribed handlers.
        """
        for handler in self._handlers.get(event.event_type, []):
            handler(event)
