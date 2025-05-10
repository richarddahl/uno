# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Protocol definitions for the events package.

This module contains the core protocols that define the interfaces for event
handling components.
"""

from __future__ import annotations

from typing import Any, Protocol, TypeVar, runtime_checkable

from uno.events.base_event import DomainEvent

E = TypeVar("E", bound=DomainEvent)


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


@runtime_checkable
class EventHandlerProtocol(Protocol):
    """
    Protocol for event handlers.
    """

    async def handle(self, context: Any) -> Any: ...


@runtime_checkable
class EventHandlerMiddlewareProtocol(Protocol):
    """
    Protocol for event handler middleware.
    """

    async def process(self, context: Any, next_middleware: Any) -> Any: ...
