# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
events.protocols
Event system protocols for Uno framework
"""

from typing import Protocol, TypeVar, Callable, Awaitable

from uno.domain.protocols import DomainEventProtocol

E = TypeVar("E", bound=DomainEventProtocol)


class EventBusProtocol(Protocol[E]):
    """Protocol for event bus implementations.

    The generic type parameter E represents the type of events this bus can handle.
    """

    def publish(self, event: E) -> None:
        """Publish a single event asynchronously.

        Args:
            event: The event to publish
        """
        ...

    def publish_many(self, events: list[E]) -> None:
        """Publish multiple events asynchronously.

        Args:
            events: List of events to publish
        """
        ...


class EventMiddlewareProtocol(Protocol[E]):
    """Protocol for event middleware.

    The generic type parameter E represents the type of events this middleware can handle.
    """

    async def process(self, event: E, next_: Callable[[E], Awaitable[None]]) -> None:
        """Process an event asynchronously.

        Args:
            event: The event to process
            next_: Callback to continue processing the event
        """
        ...


class EventHandlerProtocol(Protocol):
    """Protocol for event handlers."""

    async def handle(self, event: E) -> None: ...


class EventDispatcherProtocol(Protocol):
    """Protocol for event dispatchers."""

    def dispatch(self, event: E) -> None: ...
