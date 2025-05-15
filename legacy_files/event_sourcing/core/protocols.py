# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Protocol definitions for the event system.

This module defines the core interfaces for the event processing system,
following the Protocol-based approach for structural subtyping.
"""

from __future__ import annotations

from typing import Any, Protocol, TypeVar, Generic, runtime_checkable, Optional, Dict, List, Type, ClassVar
from datetime import datetime
import uuid

# Forward reference for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .base import DomainEvent  # noqa: F401

# Type variables for generic protocols
T = TypeVar('T')
TEvent = TypeVar('TEvent', contravariant=True)  # Input parameter type
TResult = TypeVar('TResult', covariant=True)  # Output result type

# Re-export commonly used types for backward compatibility
__all__ = [
    'EventProcessorProtocol',
    'EventHandlerProtocol',
    'EventDispatcherProtocol',
    'EventRegistryProtocol',
    'EventMiddlewareProtocol',
    'EventBusProtocol',
    'EventProtocol',
    'DomainEventProtocol',
]


@runtime_checkable
class DomainEventProtocol(Protocol):
    """Protocol defining the interface for domain events."""
    
    # Class-level attributes
    event_type: ClassVar[str]
    
    # Instance attributes
    metadata: 'EventMetadata'
    
    @property
    def event_id(self) -> str:
        """Get the event's unique identifier."""
        ...
        
    @property
    def timestamp(self) -> datetime:
        """Get when the event occurred."""
        ...


class EventMetadata:
    """Metadata associated with domain events."""
    
    def __init__(
        self,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        source: Optional[str] = None,
        version: str = "1.0",
        custom: Optional[Dict[str, Any]] = None
    ):
        self.event_id = event_id or str(uuid.uuid4())
        self.timestamp = timestamp or datetime.utcnow()
        self.correlation_id = correlation_id
        self.causation_id = causation_id
        self.user_id = user_id
        self.source = source
        self.version = version
        self.custom = custom or {}


@runtime_checkable
class EventProcessorProtocol(Protocol):
    """Protocol defining the interface for event processors."""

    async def process_event(self, event: DomainEventProtocol) -> Any:
        """Process an event and return a result."""
        ...

    async def can_process(self, event: DomainEventProtocol) -> bool:
        """Determine if this processor can handle the given event."""
        ...


@runtime_checkable
class EventHandlerProtocol(Protocol, Generic[TEvent, TResult]):
    """Protocol defining the interface for event handlers."""

    async def handle(self, event: TEvent) -> TResult:
        """Handle an event and return a result."""
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


@runtime_checkable
class EventRegistryProtocol(Protocol):
    """Protocol for event handler registries."""

    async def register(self, event_type: str, handler: Any) -> None:
        """Register a handler for an event type."""
        ...

    async def get_handlers_for_event(
        self, event: DomainEventProtocol
    ) -> List[EventHandlerProtocol[Any, Any]]:
        """Get all handlers for an event."""
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
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Process the event and pass it to the next middleware."""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Protocol for event buses."""

    async def publish(
        self, event: DomainEventProtocol, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Publish an event to registered handlers."""
        ...

    async def publish_many(
        self, events: List[DomainEventProtocol], metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Publish multiple events to registered handlers."""
        ...


@runtime_checkable
class EventProtocol(Protocol):
    """Protocol defining the interface for events."""

    @property
    def event_type(self) -> str:
        """Type of the event."""
        ...

    @property
    def payload(self) -> dict[str, Any]:
        """Event data payload."""
        ...
