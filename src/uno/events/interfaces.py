"""
Event sourcing interfaces and protocols for Uno.
Defines all core event, bus, handler, and store protocols/ABCs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol, TypeVar, Generic

from uno.events.base_event import DomainEvent  # Ensure DomainEvent is imported

E = TypeVar("E", bound=DomainEvent)
C = TypeVar("C")  # Remove bound if Command is not defined
T = TypeVar("T")


# --- Event Bus Protocols ---
class EventBusProtocol(Protocol):
    """
    Protocol for event buses (pub/sub, async/sync).
    """

    async def publish(
        self, event: E, metadata: dict[str, Any] | None = None
    ) -> None: ...
    async def publish_many(self, events: list[E]) -> None: ...


class EventPublisherProtocol(Protocol):
    """
    Protocol for event publishers (decoupled publishing interface).
    """

    async def publish(self, event: E) -> None: ...
    async def publish_many(self, events: list[E]) -> None: ...


# --- Event Handler Protocols ---
class EventHandler(ABC):
    """
    Base class for event handlers.
    """

    @abstractmethod
    async def handle(self, context: Any) -> Any:
        pass


class EventHandlerMiddleware(ABC):
    """
    Base class for event handler middleware.
    """

    @abstractmethod
    async def process(self, context: Any, next_middleware: Any) -> Any:
        pass


# --- Event Store Protocol ---
class EventStoreProtocol(Protocol, Generic[E]):
    """
    Protocol for event store implementations.
    """

    async def save_event(self, event: E) -> None: ...
    async def get_events(self, *args, **kwargs) -> list[E]: ...
    async def get_events_by_aggregate_id(
        self, aggregate_id: str, event_types: list[str] | None = None
    ) -> list[E]: ...


# --- Command Handler Protocol (CQRS) ---
class CommandHandler(Generic[C, T], ABC):
    """
    Base class for command handlers.
    """

    @abstractmethod
    async def handle(self, command: C) -> T:
        pass
