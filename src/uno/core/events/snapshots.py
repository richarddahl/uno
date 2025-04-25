"""
Snapshot management for event sourcing.

This module provides interfaces and implementations for snapshot storage
and retrieval, helping to optimize aggregate rehydration in event-sourced systems.
"""

from __future__ import annotations

# Standard library imports
from abc import ABC, abstractmethod
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Protocol, TypeVar, cast, TYPE_CHECKING

# Third-party imports
from sqlalchemy import TIMESTAMP, Column, MetaData, String, Table, insert, select
from sqlalchemy.dialects.postgresql import JSONB

# Import types only when type checking
if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from uno.core.domain.core import AggregateRoot
    from uno.core.logging.logger import LoggerService

# Application imports
from uno.core.errors.result import Failure, Result, Success


T = TypeVar("T")


class SnapshotStrategy(Protocol):
    """Protocol for deciding when to create a snapshot."""

    async def should_snapshot(self, aggregate_id: str, event_count: int) -> bool:
        """
        Determine if a snapshot should be created.

        Args:
            aggregate_id: The ID of the aggregate
            event_count: Number of events processed since last snapshot

        Returns:
            True if a snapshot should be created, False otherwise
        """
        ...


class EventCountSnapshotStrategy:
    """Create snapshots based on a threshold of new events."""

    def __init__(self, threshold: int = 10):
        """
        Initialize the strategy.

        Args:
            threshold: Number of events after which to create a snapshot
        """
        self.threshold = threshold

    async def should_snapshot(self, aggregate_id: str, event_count: int) -> bool:
        """
        Create a snapshot if the event count exceeds the threshold.

        Args:
            aggregate_id: The ID of the aggregate
            event_count: Number of events processed since last snapshot

        Returns:
            True if the event count exceeds the threshold
        """
        return event_count >= self.threshold


class TimeBasedSnapshotStrategy:
    """Create snapshots based on time elapsed since the last snapshot."""

    def __init__(self, minutes_threshold: int = 60):
        """
        Initialize the strategy.

        Args:
            minutes_threshold: Minutes after which to create a new snapshot
        """
        self.minutes_threshold = minutes_threshold
        self._last_snapshot_time: dict[str, datetime] = {}

    async def should_snapshot(self, aggregate_id: str, event_count: int) -> bool:
        """
        Create a snapshot if enough time has elapsed since the last one.

        Args:
            aggregate_id: The ID of the aggregate
            event_count: Number of events processed since last snapshot (not used)

        Returns:
            True if enough time has elapsed since the last snapshot
        """
        # If we've never made a snapshot for this aggregate, do it now
        if aggregate_id not in self._last_snapshot_time:
            self._last_snapshot_time[aggregate_id] = datetime.now(datetime.UTC)
            return True

        # Check if enough time has elapsed
        last_time = self._last_snapshot_time[aggregate_id]
        elapsed_minutes = (datetime.now(datetime.UTC) - last_time).total_seconds() / 60

        if elapsed_minutes >= self.minutes_threshold:
            self._last_snapshot_time[aggregate_id] = datetime.now(datetime.UTC)
            return True

        return False


class CompositeSnapshotStrategy:
    """Combines multiple snapshot strategies with OR logic."""

    def __init__(self, strategies: list[SnapshotStrategy]):
        """
        Initialize with a list of strategies.

        Args:
            strategies: List of snapshot strategies to use
        """
        self.strategies = strategies

    async def should_snapshot(self, aggregate_id: str, event_count: int) -> bool:
        """
        Create a snapshot if any of the underlying strategies return True.

        Args:
            aggregate_id: The ID of the aggregate
            event_count: Number of events processed since last snapshot

        Returns:
            True if any strategy returns True
        """
        for strategy in self.strategies:
            if await strategy.should_snapshot(aggregate_id, event_count):
                return True
        return False


class SnapshotStore(ABC):
    """Interface for snapshot storage and retrieval."""

    @abstractmethod
    async def save_snapshot(self, aggregate: object) -> Result[None, Exception]:
        """
        Save a snapshot of an aggregate.

        Args:
            aggregate: The aggregate to snapshot

        Returns:
            Result with None on success, or an error
        """
        ...

    @abstractmethod
    async def get_snapshot(
        self, aggregate_id: str, aggregate_type: type[T]
    ) -> Result[T | None, Exception]:
        """
        Get the latest snapshot for an aggregate.

        Args:
            aggregate_id: The ID of the aggregate
            aggregate_type: The type of the aggregate

        Returns:
            Result with the snapshot if found, None if not found, or an error
        """
        ...

    @abstractmethod
    async def delete_snapshot(self, aggregate_id: str) -> Result[None, Exception]:
        """
        Delete a snapshot.

        Args:
            aggregate_id: The ID of the aggregate

        Returns:
            Result with None on success, or an error
        """
        ...


class InMemorySnapshotStore(SnapshotStore):
    """In-memory implementation of SnapshotStore."""

    def __init__(self, logger: LoggerService):
        """
        Initialize the store.

        Args:
            logger: Logger service instance
        """
        self.logger = logger
        self._snapshots: dict[str, AggregateRoot] = {}

    async def save_snapshot(self, aggregate: AggregateRoot) -> Result[None, Exception]:
        """
        Save a snapshot in memory.

        Args:
            aggregate: The aggregate to snapshot

        Returns:
            Result with None on success, or an error
        """
        try:
            self.logger.structured_log(
                "DEBUG",
                f"Saving snapshot for aggregate {aggregate.id}",
                name="uno.events.snapshots",
            )

            self._snapshots[str(aggregate.id)] = aggregate
            return Success(None)

        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error saving snapshot: {e}",
                name="uno.events.snapshots",
                error=e,
            )
            return Failure(e)

    async def get_snapshot(
        self, aggregate_id: str, aggregate_type: type[T]
    ) -> Result[T | None, Exception]:
        """
        Get a snapshot from memory.

        Args:
            aggregate_id: The ID of the aggregate
            aggregate_type: The type of the aggregate

        Returns:
            Result with the snapshot if found, None if not found, or an error
        """
        try:
            self.logger.structured_log(
                "DEBUG",
                f"Getting snapshot for aggregate {aggregate_id}",
                name="uno.events.snapshots",
            )

            if aggregate_id in self._snapshots:
                snapshot = self._snapshots[aggregate_id]
                if isinstance(snapshot, aggregate_type):
                    self.logger.structured_log(
                        "DEBUG",
                        f"Found snapshot for aggregate {aggregate_id}",
                        name="uno.events.snapshots",
                    )
                    return Success(cast("T", snapshot))
                else:
                    self.logger.structured_log(
                        "WARN",
                        f"Snapshot type mismatch for {aggregate_id}",
                        name="uno.events.snapshots",
                    )

            self.logger.structured_log(
                "DEBUG",
                f"No snapshot found for aggregate {aggregate_id}",
                name="uno.events.snapshots",
            )
            return Success(None)

        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error getting snapshot: {e}",
                name="uno.events.snapshots",
                error=e,
            )
            return Failure(e)

    async def delete_snapshot(self, aggregate_id: str) -> Result[None, Exception]:
        """
        Delete a snapshot from memory.

        Args:
            aggregate_id: The ID of the aggregate

        Returns:
            Result with None on success, or an error
        """
        try:
            self.logger.structured_log(
                "DEBUG",
                f"Deleting snapshot for aggregate {aggregate_id}",
                name="uno.events.snapshots",
            )

            if aggregate_id in self._snapshots:
                del self._snapshots[aggregate_id]
                self.logger.structured_log(
                    "DEBUG",
                    f"Deleted snapshot for aggregate {aggregate_id}",
                    name="uno.events.snapshots",
                )

            return Success(None)

        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error deleting snapshot: {e}",
                name="uno.events.snapshots",
                error=e,
            )
            return Failure(e)


class FileSystemSnapshotStore(SnapshotStore):
    """File system implementation of SnapshotStore."""

    def __init__(self, logger: LoggerService, snapshot_dir: str = "./snapshots"):
        """
        Initialize the store.

        Args:
            logger: Logger service instance
            snapshot_dir: Directory to store snapshots
        """
        self.logger = logger
        self.snapshot_dir = Path(snapshot_dir)
        os.makedirs(self.snapshot_dir, exist_ok=True)

    def _get_snapshot_path(self, aggregate_id: str) -> Path:
        """Get the path to a snapshot file."""
        return self.snapshot_dir / f"{aggregate_id}.json"

    async def save_snapshot(self, aggregate: AggregateRoot) -> Result[None, Exception]:
        """
        Save a snapshot to the file system.

        Args:
            aggregate: The aggregate to snapshot

        Returns:
            Result with None on success, or an error
        """
        try:
            self.logger.structured_log(
                "DEBUG",
                f"Saving snapshot for aggregate {aggregate.id}",
                name="uno.events.snapshots",
            )

            # Convert aggregate to dict
            if not hasattr(aggregate, "to_dict"):
                return Failure(
                    ValueError(
                        f"Aggregate {aggregate.id} does not implement to_dict method"
                    )
                )

            aggregate_dict = aggregate.to_dict()
            aggregate_dict["_type"] = aggregate.__class__.__name__

            # Write to file
            snapshot_path = self._get_snapshot_path(str(aggregate.id))
            with open(snapshot_path, "w") as f:
                json.dump(aggregate_dict, f, default=str)

            self.logger.structured_log(
                "DEBUG",
                f"Saved snapshot for aggregate {aggregate.id}",
                name="uno.events.snapshots",
            )
            return Success(None)

        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error saving snapshot: {e}",
                name="uno.events.snapshots",
                error=e,
            )
            return Failure(e)

    async def get_snapshot(
        self, aggregate_id: str, aggregate_type: type[T]
    ) -> Result[T | None, Exception]:
        """
        Get a snapshot from the file system.

        Args:
            aggregate_id: The ID of the aggregate
            aggregate_type: The type of the aggregate

        Returns:
            Result with the snapshot if found, None if not found, or an error
        """
        try:
            self.logger.structured_log(
                "DEBUG",
                f"Getting snapshot for aggregate {aggregate_id}",
                name="uno.events.snapshots",
            )

            snapshot_path = self._get_snapshot_path(aggregate_id)
            if not snapshot_path.exists():
                self.logger.structured_log(
                    "DEBUG",
                    f"No snapshot file found for aggregate {aggregate_id}",
                    name="uno.events.snapshots",
                )
                return Success(None)

            # Read from file
            with open(snapshot_path) as f:
                aggregate_dict = json.load(f)

            # Check type
            stored_type = aggregate_dict.pop("_type", None)
            if stored_type != aggregate_type.__name__:
                self.logger.structured_log(
                    "WARN",
                    f"Snapshot type mismatch for {aggregate_id}: expected {aggregate_type.__name__}, got {stored_type}",
                    name="uno.events.snapshots",
                )
                return Success(None)

            # Check if the aggregate type has a from_dict method
            if not hasattr(aggregate_type, "from_dict"):
                return Failure(
                    ValueError(
                        f"Aggregate type {aggregate_type.__name__} does not implement from_dict method"
                    )
                )

            # Restore aggregate
            aggregate = aggregate_type.from_dict(aggregate_dict)

            self.logger.structured_log(
                "DEBUG",
                f"Retrieved snapshot for aggregate {aggregate_id}",
                name="uno.events.snapshots",
            )
            return Success(aggregate)

        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error getting snapshot: {e}",
                name="uno.events.snapshots",
                error=e,
            )
            return Failure(e)

    async def delete_snapshot(self, aggregate_id: str) -> Result[None, Exception]:
        """
        Delete a snapshot from the file system.

        Args:
            aggregate_id: The ID of the aggregate

        Returns:
            Result with None on success, or an error
        """
        try:
            self.logger.structured_log(
                "DEBUG",
                f"Deleting snapshot for aggregate {aggregate_id}",
                name="uno.events.snapshots",
            )

            snapshot_path = self._get_snapshot_path(aggregate_id)
            if snapshot_path.exists():
                os.remove(snapshot_path)
                self.logger.structured_log(
                    "DEBUG",
                    f"Deleted snapshot file for aggregate {aggregate_id}",
                    name="uno.events.snapshots",
                )

            return Success(None)

        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error deleting snapshot: {e}",
                name="uno.events.snapshots",
                error=e,
            )
            return Failure(e)


class PostgresSnapshotStore(SnapshotStore):
    """PostgreSQL implementation of SnapshotStore."""

    def __init__(self, logger: LoggerService, async_session_factory):
        """
        Initialize the store.

        Args:
            logger: Logger service instance
            async_session_factory: Factory for creating database sessions
        """
        self.logger = logger
        self.async_session_factory = async_session_factory
        self.metadata = MetaData()

        # Define snapshot table
        self.snapshots_table = Table(
            "snapshots",
            self.metadata,
            Column("aggregate_id", String, primary_key=True),
            Column("aggregate_type", String, nullable=False),
            Column("created_at", TIMESTAMP, nullable=False),
            Column("data", JSONB, nullable=False),
        )

    async def _ensure_table_exists(self, session: AsyncSession) -> None:
        """
        Make sure the snapshots table exists.

        Args:
            session: Database session
        """
        try:
            # Check if table exists by executing a simple query
            query = select(self.snapshots_table).limit(1)
            await session.execute(query)
        except Exception:
            # Table doesn't exist, create it
            await session.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                aggregate_id VARCHAR(255) PRIMARY KEY,
                aggregate_type VARCHAR(255) NOT NULL,
                created_at TIMESTAMP NOT NULL,
                data JSONB NOT NULL
            )
            """)
            await session.commit()

    async def save_snapshot(self, aggregate: AggregateRoot) -> Result[None, Exception]:
        """
        Save a snapshot to PostgreSQL.

        Args:
            aggregate: The aggregate to snapshot

        Returns:
            Result with None on success, or an error
        """
        try:
            self.logger.structured_log(
                "DEBUG",
                f"Saving snapshot for aggregate {aggregate.id}",
                name="uno.events.snapshots",
            )

            # Convert aggregate to dict
            if not hasattr(aggregate, "to_dict"):
                return Failure(
                    ValueError(
                        f"Aggregate {aggregate.id} does not implement to_dict method"
                    )
                )

            aggregate_dict = aggregate.to_dict()

            # Get a session
            async with self.async_session_factory() as session:
                await self._ensure_table_exists(session)

                # Prepare the insert
                current_time = datetime.now(datetime.UTC)
                data = {
                    "aggregate_id": aggregate.id,
                    "aggregate_type": type(aggregate).__name__,
                    "data": aggregate_dict,
                    "created_at": current_time.isoformat(),
                }
                stmt = (
                    insert(self.snapshots_table)
                    .values(data)
                    # If there's an existing snapshot, replace it
                    .on_conflict_do_update(
                        index_elements=["aggregate_id"],
                        set_={
                            "aggregate_type": aggregate.__class__.__name__,
                            "created_at": current_time.isoformat(),
                            "data": aggregate_dict,
                        },
                    )
                )

                # Execute
                await session.execute(stmt)
                await session.commit()

            self.logger.structured_log(
                "DEBUG",
                f"Saved snapshot for aggregate {aggregate.id}",
                name="uno.events.snapshots",
            )
            return Success(None)

        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error saving snapshot: {e}",
                name="uno.events.snapshots",
                error=e,
            )
            return Failure(e)

    async def get_snapshot(
        self, aggregate_id: str, aggregate_type: type[T]
    ) -> Result[T | None, Exception]:
        """
        Get a snapshot from PostgreSQL.

        Args:
            aggregate_id: The ID of the aggregate
            aggregate_type: The type of the aggregate

        Returns:
            Result with the snapshot if found, None if not found, or an error
        """
        try:
            self.logger.structured_log(
                "DEBUG",
                f"Getting snapshot for aggregate {aggregate_id}",
                name="uno.events.snapshots",
            )

            # Get a session
            async with self.async_session_factory() as session:
                await self._ensure_table_exists(session)

                # Query for the snapshot
                query = (
                    select(self.snapshots_table)
                    .where(self.snapshots_table.c.aggregate_id == aggregate_id)
                    .where(
                        self.snapshots_table.c.aggregate_type == aggregate_type.__name__
                    )
                )

                result = await session.execute(query)
                row = result.fetchone()

                if not row:
                    self.logger.structured_log(
                        "DEBUG",
                        f"No snapshot found for aggregate {aggregate_id}",
                        name="uno.events.snapshots",
                    )
                    return Success(None)

                # Get the data and restore the aggregate
                aggregate_dict = row.data

                # Check if the aggregate type has a from_dict method
                if not hasattr(aggregate_type, "from_dict"):
                    return Failure(
                        ValueError(
                            f"Aggregate type {aggregate_type.__name__} does not implement from_dict method"
                        )
                    )

                # Restore aggregate
                aggregate = aggregate_type.from_dict(aggregate_dict)

                self.logger.structured_log(
                    "DEBUG",
                    f"Retrieved snapshot for aggregate {aggregate_id}",
                    name="uno.events.snapshots",
                )
                return Success(aggregate)

        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error getting snapshot: {e}",
                name="uno.events.snapshots",
                error=e,
            )
            return Failure(e)

    async def delete_snapshot(self, aggregate_id: str) -> Result[None, Exception]:
        """
        Delete a snapshot from PostgreSQL.

        Args:
            aggregate_id: The ID of the aggregate

        Returns:
            Result with None on success, or an error
        """
        try:
            self.logger.structured_log(
                "DEBUG",
                f"Deleting snapshot for aggregate {aggregate_id}",
                name="uno.events.snapshots",
            )

            # Get a session
            async with self.async_session_factory() as session:
                await self._ensure_table_exists(session)

                # Delete the snapshot
                stmt = self.snapshots_table.delete().where(
                    self.snapshots_table.c.aggregate_id == aggregate_id
                )

                await session.execute(stmt)
                await session.commit()

                self.logger.structured_log(
                    "DEBUG",
                    f"Deleted snapshot for aggregate {aggregate_id}",
                    name="uno.events.snapshots",
                )

            return Success(None)

        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error deleting snapshot: {e}",
                name="uno.events.snapshots",
                error=e,
            )
            return Failure(e)
