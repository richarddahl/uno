"""
Event sourcing interfaces and protocols for Uno.
Defines all core event, bus, handler, and store protocols/ABCs.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Protocol, TypeVar, Generic
from uno.core.errors.result import Result

E = TypeVar("E", bound="DomainEvent")
C = TypeVar("C", bound="Command")
T = TypeVar("T")

# --- Event Bus Protocols ---
class EventBusProtocol(Protocol):
    """
    Protocol for event buses (pub/sub, async/sync).
    """
    async def publish(self, event: E, metadata: dict[str, Any] | None = None) -> Result[None, Exception]: ...
    async def publish_many(self, events: list[E]) -> Result[None, Exception]: ...

class EventPublisherProtocol(Protocol):
    """
    Protocol for event publishers (decoupled publishing interface).
    """
    async def publish(self, event: E) -> Result[None, Exception]: ...
    async def publish_many(self, events: list[E]) -> Result[None, Exception]: ...

# --- Event Handler Protocols ---
class EventHandler(ABC):
    """
    Base class for event handlers.
    """
    @abstractmethod
    async def handle(self, context: Any) -> Result[Any, Exception]:
        pass

class EventHandlerMiddleware(ABC):
    """
    Base class for event handler middleware.
    """
    @abstractmethod
    async def process(self, context: Any, next_middleware: Any) -> Result[Any, Exception]:
        pass

# --- Event Store Protocol ---
class EventStoreProtocol(Protocol, Generic[E]):
    """
    Protocol for event store implementations.
    """
    async def save_event(self, event: E) -> Result[None, Exception]: ...
    async def get_events(self, *args, **kwargs) -> Result[list[E], Exception]: ...
    async def get_events_by_aggregate_id(self, aggregate_id: str, event_types: list[str] | None = None) -> Result[list[E], Exception]: ...

# --- Command Handler Protocol (CQRS) ---
class CommandHandler(Generic[C, T], ABC):
    """
    Base class for command handlers.
    """
    @abstractmethod
    async def handle(self, command: C) -> T:
        pass
