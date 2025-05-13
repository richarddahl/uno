# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Event handling protocols.

This module provides the protocol definitions for the event system components,
enabling structural typing and loose coupling.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from uno.domain.protocols import DomainEventProtocol


@runtime_checkable
class EventHandlerProtocol(Protocol):
    """Protocol for event handlers."""

    async def handle(
        self, event: DomainEventProtocol, metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Handle the event.

        Args:
            event: The domain event to handle
            metadata: Optional metadata associated with the event

        Raises:
            EventHandlerError: If the handler encounters an error
        """
        ...


@runtime_checkable
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
    ) -> list[EventHandlerProtocol]:
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


@runtime_checkable
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


@runtime_checkable
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
