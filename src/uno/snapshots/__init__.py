"""Snapshot management for event-sourced aggregates."""

from uno.snapshots.protocols import (
    EventCountSnapshotStrategyProtocol,
    SnapshotProtocol,
    SnapshotStoreProtocol,
    SnapshotStrategyProtocol,
    TimeBasedSnapshotStrategyProtocol,
)

__all__ = [
    "EventCountSnapshotStrategyProtocol",
    "SnapshotProtocol",
    "SnapshotStoreProtocol",
    "SnapshotStrategyProtocol",
    "TimeBasedSnapshotStrategyProtocol",
]
