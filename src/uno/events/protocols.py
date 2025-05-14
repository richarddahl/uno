# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Protocol definitions for the events package.

This module defines interfaces for the event processing system.
"""

from __future__ import annotations

from typing import Any, Protocol
from typing import TypeVar, Generic

from uno.domain.protocols import DomainEventProtocol

# Define type variables for generic protocols
T = TypeVar("T")
TEvent = TypeVar("TEvent", contravariant=True)  # Input parameter type
TResult = TypeVar("TResult", covariant=True)  # Output result type


class EventProcessorProtocol(Protocol):
    """Protocol defining the interface for event processors."""

    async def process_event(self, event: Any) -> Any:
        """
        Process an event and return a result.

        Args:
            event: Any
                The event to process.

        Returns:
            Any: The result of processing the event.
        """
        ...

    async def can_process(self, event: Any) -> bool:
        """
        Determine if this processor can handle the given event.

        Args:
            event: Any
                The event to check.

        Returns:
            bool: True if the processor can handle the event, False otherwise.
        """
        ...


class EventHandlerProtocol(Protocol, Generic[TEvent, TResult]):
    """Protocol defining the interface for event handlers."""

    async def handle(self, event: TEvent) -> TResult:
        """
        Handle an event and return a result.

        Args:
            event: TEvent
                The event to handle.

        Returns:
            TResult: The result of handling the event.
        """
        ...


class EventDispatcherProtocol(Protocol):
    """Protocol defining the interface for event dispatchers."""

    async def dispatch(self, event: Any) -> Any:
        """
        Dispatch an event to appropriate handlers and return the result.

        Args:
            event: Any
                The event to dispatch.

        Returns:
            Any: The result of dispatching the event.
        """
        ...

    async def register_handler(self, handler: EventHandlerProtocol[Any, Any]) -> None:
        """
        Register an event handler with the dispatcher.

        Args:
            handler: EventHandlerProtocol[Any, Any]
                The event handler to register.
        """
        ...

    async def unregister_handler(self, handler: EventHandlerProtocol[Any, Any]) -> None:
        """
        Unregister an event handler from the dispatcher.

        Args:
            handler: EventHandlerProtocol[Any, Any]
                The event handler to unregister.
        """
        ...


class EventRegistryProtocol(Protocol):
    """Protocol for event handler registries."""

    async def register(self, event_type: str, handler: Any) -> None:
        """
        Register a handler for an event type.

        Args:
            event_type: The event type to register a handler for
            handler: The handler to register (can be any callable or handler implementation)
        """
        ...

    async def get_handlers_for_event(
        self, event: DomainEventProtocol
    ) -> list[EventHandlerProtocol[Any, Any]]:
        """
        Get all handlers for an event.

        Args:
            event: The domain event to get handlers for

        Returns:
            List of handlers for the event
        """
        ...

    async def clear(self) -> None:
        """Clear all handlers in the registry."""
        ...


class EventMiddlewareProtocol(Protocol):
    """Protocol for event handler middleware."""

    async def process(
        self,
        event: DomainEventProtocol,
        next_middleware: Any,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Process the event and pass it to the next middleware.

        Args:
            event: The domain event to process
            next_middleware: The next middleware in the chain
            metadata: Optional event metadata

        Raises:
            EventHandlerError: If an error occurs during processing
        """
        ...


class EventBusProtocol(Protocol):
    """Protocol for event buses."""

    async def publish(
        self, event: DomainEventProtocol, metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Publish an event to registered handlers.

        Args:
            event: The event to publish
            metadata: Optional metadata for the event

        Raises:
            EventHandlerError: If any handler fails
        """
        ...

    async def publish_many(
        self, events: list[DomainEventProtocol], metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Publish multiple events to registered handlers.

        Args:
            events: The events to publish
            metadata: Optional metadata for the events

        Raises:
            EventHandlerError: If any handler fails
        """
        ...


class EventProtocol(Protocol):
    """Protocol for events that can be dispatched through the event system."""

    @property
    def event_id(self) -> str:
        """Unique identifier for this event instance."""
        ...

    @property
    def event_type(self) -> str:
        """Type of the event."""
        ...

    @property
    def payload(self) -> dict[str, Any]:
        """Event data payload."""
        ...


class EventHandlerProtocol(Protocol):
    """Protocol for event handlers."""

    async def handle(self, event: EventProtocol) -> None:
        """Handle an event."""
        ...


class EventHandlerRegistryProtocol(Protocol):
    """Protocol for event handler registries."""

    def register(self, handler: EventHandlerProtocol) -> None:
        """Register a handler for a specific event type."""
        ...

    def get_handlers_for(
        self, event_type: type[EventProtocol]
    ) -> list[EventHandlerProtocol]:
        """Get all handlers registered for a specific event type."""
        ...

    def clear(self) -> None:
        """Clear all registered handlers."""
        ...
