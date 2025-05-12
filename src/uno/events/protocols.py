# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Protocol definitions for the events package.

This module contains the core protocols that define the interfaces for event
handling components.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, TypeVar, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Callable

from uno.domain.protocols import DomainEventProtocol

E = TypeVar("E", bound=DomainEventProtocol)


@runtime_checkable
class EventBusProtocol(Protocol):
    """
    Protocol for event buses (pub/sub, async/sync).

    Event buses are responsible for publishing events to registered handlers
    and subscribing handlers to event types.
    """

    async def publish(self, event: E, context: dict[str, Any] | None = None) -> None:
        """
        Publish an event to registered handlers.

        Args:
            event: The domain event to publish
            context: Optional context information for event processing
        """
        ...

    async def publish_many(
        self, events: list[E], context: dict[str, Any] | None = None
    ) -> None:
        """
        Publish multiple events to registered handlers.

        Args:
            events: The domain events to publish
            context: Optional context information for event processing
        """
        ...

    async def subscribe(self, event_type: str, handler: EventHandlerProtocol) -> None:
        """
        Subscribe a handler to an event type.

        Args:
            event_type: The event type to subscribe to
            handler: The handler to register for the event type
        """
        ...


@runtime_checkable
class EventPublisherProtocol(Protocol):
    """
    Protocol for event publishers (decoupled publishing interface).

    Event publishers provide a decoupled interface for publishing events
    without direct knowledge of handlers.
    """

    async def publish(self, event: E, context: dict[str, Any] | None = None) -> None:
        """
        Publish an event.

        Args:
            event: The domain event to publish
            context: Optional context information for event processing
        """
        ...

    async def publish_many(
        self, events: list[E], context: dict[str, Any] | None = None
    ) -> None:
        """
        Publish multiple events.

        Args:
            events: The domain events to publish
            context: Optional context information for event processing
        """
        ...


@runtime_checkable
class EventHandlerProtocol(Protocol):
    """
    Protocol for event handlers.

    Defines the interface for handling domain events. Handlers implementing
    this protocol can process events through their handle method.
    """

    async def handle(
        self, event: DomainEventProtocol, context: dict[str, Any] | None = None
    ) -> None:
        """
        Handle a domain event.

        Args:
            event: The domain event to handle
            context: Optional context information for event processing
        """
        ...


@runtime_checkable
class SnapshotStrategy(Protocol):
    """Protocol for deciding when to create a snapshot.

    Canonical serialization contract for snapshots:
      - Always use `model_dump(exclude_none=True, exclude_unset=True, by_alias=True, sort_keys=True)` for snapshot serialization, storage, and integrity checks.
      - Unset and None fields are treated identically; excluded from serialization and hashing.
      - This contract is enforced by dedicated tests.
    """

    async def should_snapshot(self, aggregate_id: str, event_count: int) -> bool:
        """
        Determine if a snapshot should be created.

        Args:
            aggregate_id: The ID of the aggregate
            event_count: Number of events processed since last snapshot

        Returns:
            True if a snapshot should be created, False otherwise
        """
        ...


@runtime_checkable
class EventMiddlewareProtocol(Protocol):
    """
    Protocol for event middleware.

    Defines the interface for middleware that can intercept and modify
    event processing behavior.
    """

    async def process(
        self,
        event: DomainEventProtocol,
        context: dict[str, Any] | None,
        next_middleware: Callable[[DomainEventProtocol, dict[str, Any] | None], Any],
    ) -> None:
        """
        Process an event through the middleware chain.

        Args:
            event: The domain event to process
            context: Optional context information for event processing
            next_middleware: The next middleware in the chain to call
        """
        ...


@runtime_checkable
class EventRegistryProtocol(Protocol):
    """
    Protocol for event handler registries.

    Defines the interface for registering event handlers and retrieving handlers
    for specific event types.
    """

    async def register(self, event_type: str, handler: EventHandlerProtocol) -> None:
        """
        Register an event handler for a specific event type.

        Args:
            event_type: The event type the handler can process
            handler: The event handler to register
        """
        ...

    async def get_handlers_for_event(
        self, event: DomainEventProtocol
    ) -> list[EventHandlerProtocol]:
        """
        Get all handlers that can process the given event.

        Args:
            event: The domain event to get handlers for

        Returns:
            A list of handlers that can process the event
        """
        ...

    async def clear(self) -> None:
        """Clear all handlers in the registry."""
        ...


@runtime_checkable
class EventProcessorProtocol(Protocol):
    """
    Protocol for event processors.

    Defines the interface for processing events with registered handlers.
    Event processors coordinate the invocation of handlers for events.
    """

    async def process(
        self,
        event: DomainEventProtocol,
        context: dict[str, Any] | None = None,
    ) -> None:
        """
        Process an event with all registered handlers.

        Args:
            event: The domain event to process
            context: Optional context information for event processing
        """
        ...

    async def process_with_cancellation(
        self,
        event: DomainEventProtocol,
        context: dict[str, Any] | None = None,
        cancellation_token: Any = None,
    ) -> None:
        """
        Process an event with all registered handlers, with cancellation support.

        Args:
            event: The domain event to process
            context: Optional context information for event processing
            cancellation_token: Token that can be used to cancel processing

        Raises:
            asyncio.CancelledError: If event processing is cancelled
        """
        ...


@runtime_checkable
class EventDiscoveryProtocol(Protocol):
    """
    Protocol for event handler discovery services.

    Defines the interface for discovering event handlers in modules
    and registering them with a registry.
    """

    async def discover_handlers(
        self,
        package: str | object,
        registry: EventRegistryProtocol | None = None,
    ) -> EventRegistryProtocol:
        """
        Discover event handlers in a package.

        Args:
            package: The package or module to scan for handlers
            registry: Optional registry to register handlers with

        Returns:
            The registry with discovered handlers
        """
        ...


@runtime_checkable
class SerializationProtocol(Protocol):
    """
    Protocol for serializable events.

    Provides the interface for event serialization and deserialization.
    """

    event_type: str
    version: int

    def serialize(self) -> dict[str, Any]:
        """
        Serialize the event to a dictionary.

        Returns:
            A dictionary representation of the event.
        """
        ...

    @classmethod
    def deserialize(
        cls: type[SerializationProtocol], data: dict[str, Any]
    ) -> SerializationProtocol:
        """
        Deserialize an event from a dictionary.

        Args:
            data: A dictionary containing event data.

        Returns:
            An instance of the event.
        """
        ...
