"""Snapshot strategy implementations for memory-based storage."""

from __future__ import annotations

from datetime import datetime, timezone


class EventCountSnapshotStrategy:
    """Strategy for taking snapshots based on the number of events."""

    def __init__(self, threshold: int = 10) -> None:
        """
        Initialize the event count snapshot strategy.

        Args:
            threshold: Number of events after which to take a snapshot
        """
        self.threshold = threshold

    async def should_snapshot(self, aggregate_id: str, current_version: int) -> bool:
        """
        Determine if a snapshot should be taken based on event count.

        Args:
            aggregate_id: The ID of the aggregate
            current_version: The current version of the aggregate

        Returns:
            bool: True if a snapshot should be taken, False otherwise
        """
        return current_version >= self.threshold and current_version > 0


class TimeBasedSnapshotStrategy:
    """Strategy for taking snapshots based on time intervals."""
    
    def __init__(self, minutes_threshold: int = 60) -> None:
        """
        Initialize the time-based snapshot strategy.
        
        Args:
            minutes_threshold: Maximum age in minutes before taking a new snapshot
        """
        self.max_age_seconds = minutes_threshold * 60
        self._last_snapshot_time: dict[str, datetime] = {}

    async def should_snapshot(self, aggregate_id: str, current_version: int) -> bool:
        """
        Determine if a snapshot should be taken based on time elapsed.
        
        Args:
            aggregate_id: The ID of the aggregate
            current_version: The current version of the aggregate
            
        Returns:
            bool: True if a snapshot should be taken, False otherwise
        """
        now = datetime.now(timezone.utc)
        
        # If we've never taken a snapshot for this aggregate, we should take one
        if aggregate_id not in self._last_snapshot_time:
            self._last_snapshot_time[aggregate_id] = now
            return True
            
        # Calculate time since last snapshot
        last_time = self._last_snapshot_time[aggregate_id]
        time_since_last = (now - last_time).total_seconds()
        
        # Take a new snapshot if enough time has passed
        if time_since_last >= self.max_age_seconds:
            self._last_snapshot_time[aggregate_id] = now
            return True
            
        return False


class CompositeSnapshotStrategy:
    """Strategy that combines multiple snapshot strategies with OR logic.
    
    A snapshot will be taken if any of the component strategies returns True.
    """
    
    def __init__(self, *strategies) -> None:
        """
        Initialize the composite strategy.
        
        Args:
            *strategies: One or more strategy instances to combine, or a single iterable of strategies
        """
        # Handle case where a single iterable is passed
        if len(strategies) == 1 and hasattr(strategies[0], '__iter__') and not isinstance(strategies[0], str):
            self.strategies = list(strategies[0])
        else:
            self.strategies = list(strategies)
    
    async def should_snapshot(self, aggregate_id: str, current_version: int) -> bool:
        """
        Determine if a snapshot should be taken by checking all strategies.
        
        Args:
            aggregate_id: The ID of the aggregate
            current_version: The current version of the aggregate
            
        Returns:
            bool: True if any strategy returns True, False otherwise
        """
        for strategy in self.strategies:
            if await strategy.should_snapshot(aggregate_id, current_version):
                return True
        return False
