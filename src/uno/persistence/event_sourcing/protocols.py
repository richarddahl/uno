# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Protocol definitions for event sourcing persistence.

This module contains protocols specific to event sourcing persistence.
"""

from __future__ import annotations

from typing import Any, Protocol, TypeVar

from uno.events.base import DomainEvent

E = TypeVar("E", bound=DomainEvent)


class EventStoreProtocol(Protocol[E]):
    """
    Protocol for event store implementations.

    Defines the interface for components that store and retrieve domain events.
    """

    async def save_event(self, event: E) -> None: ...
    async def get_events(self, *args: Any, **kwargs: Any) -> list[E]: ...
    async def get_events_by_aggregate_id(
        self, aggregate_id: str, event_types: list[str] | None = None
    ) -> list[E]: ...
