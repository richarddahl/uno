# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
event_store.protocols
Event store protocols for Uno framework
"""

from __future__ import annotations

from typing import Protocol, TypeVar, AsyncIterator, Any, Optional
from datetime import datetime
from uuid import UUID

from uno.domain.protocols import DomainEventProtocol

E = TypeVar("E", bound=DomainEventProtocol)


class EventStoreProtocol(Protocol[E]):
    """Protocol for event store implementations."""

    async def append(
        self,
        aggregate_id: UUID,
        events: list[E],
        expected_version: int | None = None,
    ) -> None:
        """Append events to an aggregate's stream.

        Args:
            aggregate_id: The ID of the aggregate
            events: List of events to append
            expected_version: Expected current version of the aggregate

        Raises:
            EventStoreError: If append fails
        """
        ...

    async def get_events(
        self,
        aggregate_id: str,
        from_version: int = 0,
        to_version: int | None = None,
    ) -> AsyncIterator[E]:
        """Get events for an aggregate.

        Args:
            aggregate_id: The ID of the aggregate
            from_version: Starting version (inclusive). Defaults to 0.
            to_version: Ending version (inclusive). If None, gets all events.

        Yields:
            Events in order from oldest to newest

        Raises:
            EventStoreGetEventsError: If event retrieval fails
        """
        ...

    async def replay_events(
        self,
        aggregate_id: UUID,
        from_version: int | None = None,
        to_version: int | None = None,
    ) -> AsyncIterator[E]:
        """Replay events for an aggregate.

        Args:
            aggregate_id: The ID of the aggregate
            from_version: Optional starting version
            to_version: Optional ending version

        Yields:
            Events in order from oldest to newest

        Raises:
            EventStoreReplayError: If replay fails
        """
        ...

    async def get_snapshot(
        self,
        aggregate_id: UUID,
    ) -> E | None:
        """Get the latest snapshot for an aggregate.

        Args:
            aggregate_id: The ID of the aggregate

        Returns:
            The latest snapshot event, or None if no snapshot exists

        Raises:
            EventStoreError: If snapshot retrieval fails
        """
        ...

    async def create_snapshot(
        self,
        aggregate_id: UUID,
        version: int,
        state: dict[str, Any],
    ) -> None:
        """Create a snapshot for an aggregate.

        Args:
            aggregate_id: The ID of the aggregate
            version: The version of the snapshot
            state: The aggregate state to snapshot

        Raises:
            EventStoreError: If snapshot creation fails
        """
        ...
