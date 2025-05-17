# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
event_store.memory
In-memory event store implementation for Uno framework
"""

from __future__ import annotations
from typing import TypeVar, Generic, AsyncIterator, Any
from uuid import UUID
from datetime import datetime, UTC

from uno.domain.events import DomainEvent
from uno.event_store.errors import (
    EventStoreAppendError,
    EventStoreGetEventsError,
    EventStoreSnapshotError,
    EventStoreVersionConflict,
)

E = TypeVar('E', bound=DomainEvent)

class InMemoryEventStore(Generic[E]):
    """In-memory implementation of the event store."""

    def __init__(self) -> None:
        self._events: dict[UUID, list[E]] = {}
        self._snapshots: dict[UUID, E] = {}
        self._versions: dict[UUID, int] = {}
        self._metadata: dict[UUID, dict[str, Any]] = {}

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
            EventStoreVersionConflict: If version conflict occurs
            EventStoreAppendError: If append fails
        """
        try:
            current_version = self._versions.get(aggregate_id, 0)
            
            if expected_version is not None and expected_version != current_version:
                raise EventStoreVersionConflict(
                    f"Version conflict for aggregate {aggregate_id}. Expected {expected_version}, got {current_version}",
                    context={
                        "aggregate_id": str(aggregate_id),
                        "expected_version": expected_version,
                        "current_version": current_version,
                    }
                )

            # Store events with metadata and validate versions
            current_version = self._versions.get(aggregate_id, 0)
            expected_next_version = current_version + 1
            
            for event in events:
                if event.event_id not in self._metadata:
                    self._metadata[event.event_id] = {}
                self._metadata[event.event_id].update(event.metadata)
                
                # Validate event versioning
                if event.version != 1:
                    raise EventStoreVersionConflict(
                        f"Event version must be 1 for new events. Got {event.version}",
                        context={
                            "event_id": str(event.event_id),
                            "event_version": event.version,
                            "aggregate_id": str(aggregate_id),
                        }
                    )
                
                event.aggregate_version = expected_next_version
                expected_next_version += 1
            
            event_list = self._events.setdefault(aggregate_id, [])
            event_list.extend(events)
            self._versions[aggregate_id] = expected_next_version - 1

        except Exception as e:
            raise EventStoreAppendError(
                f"Failed to append events for aggregate {aggregate_id}: {str(e)}",
                context={
                    "aggregate_id": str(aggregate_id),
                    "events_count": len(events),
                    "error": str(e),
                }
            )

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
        try:
            events = self._events.get(aggregate_id, [])
            
            if from_version is not None:
                events = [e for e in events if e.aggregate_version >= from_version]
            
            if to_version is not None:
                events = [e for e in events if e.aggregate_version <= to_version]
            
            for event in events:
                # Add metadata to the event
                event.metadata = self._metadata.get(event.event_id, {})
                yield event

        except Exception as e:
            raise EventStoreReplayError(
                f"Failed to replay events for aggregate {aggregate_id}: {str(e)}",
                context={
                    "aggregate_id": str(aggregate_id),
                    "from_version": from_version,
                    "to_version": to_version,
                    "error": str(e),
                }
            )

    async def get_events(
        self,
        aggregate_id: UUID,
        from_version: int | None = None,
    ) -> AsyncIterator[E]:
        """Get events for an aggregate.

        Args:
            aggregate_id: The ID of the aggregate
            from_version: Optional starting version

        Yields:
            Events in order from oldest to newest

        Raises:
            EventStoreGetEventsError: If event retrieval fails
        """
        try:
            events = self._events.get(aggregate_id, [])
            
            if from_version is not None:
                events = [e for e in events if e.aggregate_version >= from_version]
            
            for event in events:
                # Add metadata to the event
                event.metadata = self._metadata.get(event.event_id, {})
                yield event

        except Exception as e:
            raise EventStoreGetEventsError(
                f"Failed to get events for aggregate {aggregate_id}: {str(e)}",
                context={
                    "aggregate_id": str(aggregate_id),
                    "from_version": from_version,
                    "error": str(e),
                }
            )

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
            EventStoreSnapshotError: If snapshot retrieval fails
        """
        try:
            return self._snapshots.get(aggregate_id)

        except Exception as e:
            raise EventStoreSnapshotError(
                f"Failed to get snapshot for aggregate {aggregate_id}: {str(e)}",
                context={
                    "aggregate_id": str(aggregate_id),
                    "error": str(e),
                }
            )

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
            EventStoreSnapshotError: If snapshot creation fails
        """
        try:
            if aggregate_id not in self._events:
                raise EventStoreSnapshotError(
                    f"Cannot create snapshot for non-existent aggregate {aggregate_id}",
                    context={
                        "aggregate_id": str(aggregate_id),
                        "version": version,
                    }
                )

            current_version = self._versions.get(aggregate_id, 0)
            if version > current_version:
                raise EventStoreSnapshotError(
                    f"Cannot create snapshot with future version {version} for aggregate {aggregate_id}",
                    context={
                        "aggregate_id": str(aggregate_id),
                        "version": version,
                        "current_version": current_version,
                    }
                )

            # Create a snapshot event
            snapshot_event = DomainEvent(
                event_id=UUID(int=0),  # Special ID for snapshot
                event_type="Snapshot",
                occurred_on=datetime.now(UTC),
                version=version,
                state=state,
            )
            
            # Store the snapshot event
            self._snapshots[aggregate_id] = snapshot_event  # type: ignore[assignment]  # mypy will verify this at compile time  

        except Exception as e:
            raise EventStoreSnapshotError(
                f"Failed to create snapshot for aggregate {aggregate_id}: {str(e)}",
                context={
                    "aggregate_id": str(aggregate_id),
                    "version": version,
                    "error": str(e),
                }
            )
