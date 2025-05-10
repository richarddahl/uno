# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Protocol definitions for the events package.

This module contains the core protocols that define the interfaces for the event
sourcing system components.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

E = TypeVar("E", bound="DomainEvent")
C = TypeVar("C")  # Generic command type
T = TypeVar("T")


@runtime_checkable
class EventBusProtocol(Protocol):
    """
    Protocol for event buses (pub/sub, async/sync).
    """

    async def publish(
        self, event: E, metadata: dict[str, Any] | None = None
    ) -> None: ...
    async def publish_many(self, events: list[E]) -> None: ...


@runtime_checkable
class EventPublisherProtocol(Protocol):
    """
    Protocol for event publishers (decoupled publishing interface).
    """

    async def publish(self, event: E) -> None: ...
    async def publish_many(self, events: list[E]) -> None: ...


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


@runtime_checkable
class EventStoreProtocol(Protocol, Generic[E]):
    """
    Protocol for event store implementations.
    """

    async def save_event(self, event: E) -> None: ...
    async def get_events(self, *args: Any, **kwargs: Any) -> list[E]: ...
    async def get_events_by_aggregate_id(
        self, aggregate_id: str, event_types: list[str] | None = None
    ) -> list[E]: ...


class CommandHandler(Generic[C, T], ABC):
    """
    Base class for command handlers.
    """

    @abstractmethod
    async def handle(self, command: C) -> T:
        pass
