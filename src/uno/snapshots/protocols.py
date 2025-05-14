"""Protocol definitions for the snapshot system."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol


class SnapshotProtocol(Protocol):
    """Protocol defining the structure of snapshots used for aggregate rehydration."""

    aggregate_id: str
    aggregate_version: int
    created_at: datetime
    state: dict[str, Any]


class SnapshotStrategyProtocol(Protocol):
    """Protocol defining how snapshots are triggered during event processing."""

    async def should_snapshot(self, aggregate_id: str, current_version: int) -> bool:
        """
        Determine if a snapshot should be taken for the given aggregate at its current version.

        Args:
            aggregate_id: The ID of the aggregate
            current_version: The current version of the aggregate

        Returns:
            bool: True if a snapshot should be taken, False otherwise
        """
        ...


class SnapshotStoreProtocol(Protocol):
    """Protocol defining storage and retrieval operations for snapshots."""

    async def save_snapshot(
        self, aggregate_id: str, aggregate_version: int, state: dict[str, Any]
    ) -> None:
        """
        Save a snapshot of an aggregate.

        Args:
            aggregate_id: The ID of the aggregate
            aggregate_version: The version of the aggregate
            state: The serialized state of the aggregate
        """
        ...

    async def get_latest_snapshot(self, aggregate_id: str) -> SnapshotProtocol | None:
        """
        Get the latest snapshot for an aggregate.

        Args:
            aggregate_id: The ID of the aggregate

        Returns:
            SnapshotProtocol | None: The latest snapshot if available, None otherwise
        """
        ...

    async def delete_snapshots(self, aggregate_id: str) -> None:
        """
        Delete all snapshots for an aggregate.

        Args:
            aggregate_id: The ID of the aggregate
        """
        ...


class EventCountSnapshotStrategyProtocol(SnapshotStrategyProtocol, Protocol):
    """Protocol for snapshot strategies based on event count."""

    frequency: int


class TimeBasedSnapshotStrategyProtocol(SnapshotStrategyProtocol, Protocol):
    """Protocol for snapshot strategies based on time intervals."""

    max_age_seconds: int
    last_snapshot_time: dict[str, datetime]
