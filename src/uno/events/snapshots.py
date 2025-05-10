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

from uno.events.errors import EventStoreError
from uno.errors.base import UnoError


# Third-party imports
from sqlalchemy import TIMESTAMP, Column, MetaData, String, Table, insert, select
from sqlalchemy.dialects.postgresql import JSONB

# Import types only when type checking
if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from uno.domain.core import AggregateRoot
    from uno.logging.protocols import LoggerProtocol

# Application imports



T = TypeVar("T")




class SnapshotStrategy(Protocol):
    """Protocol for deciding when to create a snapshot.

    Canonical serialization contract for snapshots:
      - Always use `model_dump(exclude_none=True, exclude_unset=True, by_alias=True, sort_keys=True)` for snapshot serialization, storage, and integrity checks.
      - Unset and None fields are treated identically; excluded from serialization and hashing.
      - This contract is enforced by dedicated tests.
    """

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
    async def save_snapshot(self, aggregate: object) -> None:
        """
        Save a snapshot of the aggregate.
        Raises:
            UnoError: if saving fails
        """
        """
        Save a snapshot of an aggregate.

        Args:
            aggregate: The aggregate to snapshot

        Returns:
            None
        Raises:
            UnoError: if saving fails
        """
        ...

    @abstractmethod
    async def get_snapshot(
        self, aggregate_id: str, aggregate_type: type[T]
    ) -> T | None:
        """
        Get a snapshot of the aggregate.
        Returns:
            The snapshot if found, None if not found.
        Raises:
            UnoError: if retrieval fails
        """
        """
        Get the latest snapshot for an aggregate.

        Args:
            aggregate_id: The ID of the aggregate
            aggregate_type: The type of the aggregate

        Returns:
            The snapshot if found, None if not found.
        Raises:
            UnoError: if retrieval fails
        """
        ...

    @abstractmethod
    async def delete_snapshot(self, aggregate_id: str) -> None:
        """
        Delete a snapshot by aggregate ID.
        Raises:
            UnoError: if deletion fails
        """
        """
        Delete a snapshot.

        Args:
            aggregate_id: The ID of the aggregate

        Returns:
            None
        Raises:
            UnoError: if saving fails
        """
        ...


class InMemorySnapshotStore(SnapshotStore):
    """In-memory implementation of SnapshotStore."""

    def __init__(self, logger: LoggerProtocol):
        """
        Initialize the store.

        Args:
            logger: Logger service instance
        """
        self.logger = logger
        self._snapshots: dict[str, AggregateRoot] = {}

    async def save_snapshot(self, aggregate: AggregateRoot) -> None:
        """
        Save a snapshot in memory.

        Args:
            aggregate: The aggregate to snapshot

        Raises:
            UnoError: If saving fails.
        """
        try:
            self.logger.structured_log(
                "DEBUG",
                f"Saving snapshot for aggregate {aggregate.id}",
                name="uno.events.snapshots",
            )
            self._snapshots[str(aggregate.id)] = aggregate
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error saving snapshot: {e}",
                name="uno.events.snapshots",
                error=e,
            )
            raise UnoError.wrap(e, message="Failed to save in-memory snapshot")

    async def get_snapshot(self, aggregate_id: str, aggregate_type: type[T]) -> T | None:
        """
        Get a snapshot from memory.

        Args:
            aggregate_id: The ID of the aggregate
            aggregate_type: The type of the aggregate

        Returns:
            The snapshot if found and type matches, or None if not found.

        Raises:
            UnoError: If retrieval fails.
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
                    return cast(T, snapshot)
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
            return None
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error getting snapshot: {e}",
                name="uno.events.snapshots",
                error=e,
            )
            raise UnoError.wrap(e, message="Failed to get in-memory snapshot")

    async def delete_snapshot(self, aggregate_id: str) -> None:
        """
        Delete a snapshot from memory.

        Args:
            aggregate_id: The ID of the aggregate

        Raises:
            UnoError: If deletion fails.
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
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error deleting snapshot: {e}",
                name="uno.events.snapshots",
                error=e,
            )
            raise UnoError.wrap(e, message="Failed to delete in-memory snapshot")


class FileSystemSnapshotStore(SnapshotStore):
    """File system implementation of SnapshotStore."""

    def __init__(self, logger: LoggerProtocol, snapshot_dir: str = "./snapshots"):
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

    def _canonical_snapshot_dict(self, aggregate: AggregateRoot) -> dict[str, object]:
        """
        Canonical snapshot serialization for storage and integrity.
        Uses model_dump(exclude_none=True, exclude_unset=True, by_alias=True) (Uno contract, Pydantic v2 compliant).
        """
        return aggregate.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True
        )

    async def save_snapshot(self, aggregate: AggregateRoot) -> None:
        """
        Save a snapshot to the file system.

        All persisted snapshots are first serialized using the canonical pattern via self._canonical_snapshot_dict(aggregate).
        This guarantees deterministic, tamper-evident storage and transport.

        Args:
            aggregate: The aggregate to snapshot

        Raises:
            UnoError: If saving fails or aggregate is invalid.
        """
        try:
            aggregate_id = getattr(aggregate, "id", None)
            if not aggregate_id:
                raise UnoError("Aggregate must have an id field")
            path = self._get_snapshot_path(aggregate_id)
            canonical_snapshot = self._canonical_snapshot_dict(aggregate)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(canonical_snapshot, f, ensure_ascii=False, sort_keys=True)
            self.logger.structured_log(
                "DEBUG",
                f"Saved snapshot for aggregate {aggregate_id}",
                name="uno.events.snapshots",
            )
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error saving snapshot: {e}",
                name="uno.events.snapshots",
                error=e,
            )
            raise UnoError.wrap(e, message="Failed to save file system snapshot")

    async def get_snapshot(self, aggregate_id: str, aggregate_type: type[T]) -> T | None:
        """
        Get a snapshot from the file system.

        Args:
            aggregate_id: The ID of the aggregate
            aggregate_type: The type of the aggregate

        Returns:
            The snapshot if found and type matches, or None if not found.

        Raises:
            UnoError: If retrieval or deserialization fails.
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
                return None
            with open(snapshot_path) as f:
                aggregate_dict = json.load(f)
            stored_type = aggregate_dict.pop("_type", None)
            if stored_type != aggregate_type.__name__:
                self.logger.structured_log(
                    "WARN",
                    f"Snapshot type mismatch for {aggregate_id}: expected {aggregate_type.__name__}, got {stored_type}",
                    name="uno.events.snapshots",
                )
                return None
            if not hasattr(aggregate_type, "from_dict"):
                raise UnoError(f"Aggregate type {aggregate_type.__name__} does not implement from_dict method")
            aggregate = aggregate_type.from_dict(aggregate_dict)
            self.logger.structured_log(
                "DEBUG",
                f"Retrieved snapshot for aggregate {aggregate_id}",
                name="uno.events.snapshots",
            )
            return aggregate
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error getting snapshot: {e}",
                name="uno.events.snapshots",
                error=e,
            )
            raise UnoError.wrap(e, message="Failed to get file system snapshot")

    async def delete_snapshot(self, aggregate_id: str) -> None:
        """
        Delete a snapshot from the file system.

        Args:
            aggregate_id: The ID of the aggregate

        Raises:
            UnoError: If deletion fails.
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
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error deleting snapshot: {e}",
                name="uno.events.snapshots",
                error=e,
            )
            raise UnoError.wrap(e, message="Failed to delete file system snapshot")


class PostgresSnapshotStore(SnapshotStore):
    """PostgreSQL implementation of SnapshotStore."""

    def __init__(self, logger: LoggerProtocol, async_session_factory):
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
            await session.execute(
                """
            CREATE TABLE IF NOT EXISTS snapshots (
                aggregate_id VARCHAR(255) PRIMARY KEY,
                aggregate_type VARCHAR(255) NOT NULL,
                created_at TIMESTAMP NOT NULL,
                data JSONB NOT NULL
            )
            """
            )
            await session.commit()

    async def save_snapshot(self, aggregate: AggregateRoot) -> None:
        """
        Save a snapshot to PostgreSQL.

        Args:
            aggregate: The aggregate to snapshot

        Raises:
            UnoError: If saving fails or aggregate is invalid.
        """
        try:
            self.logger.structured_log(
                "DEBUG",
                f"Saving snapshot for aggregate {aggregate.id}",
                name="uno.events.snapshots",
            )
            if not hasattr(aggregate, "to_dict"):
                raise UnoError(f"Aggregate {aggregate.id} does not implement to_dict method")
            aggregate_dict = aggregate.to_dict()
            async with self.async_session_factory() as session:
                await self._ensure_table_exists(session)
                current_time = datetime.now(datetime.UTC)
                data = {
                    "aggregate_id": aggregate.id,
                    "aggregate_type": type(aggregate).__name__,
                    "data": aggregate_dict,
                    "created_at": current_time.isoformat(),
                }
                stmt = (
                    insert(self.snapshots_table).values(data)
                    .on_conflict_do_update(
                        index_elements=["aggregate_id"],
                        set_={
                            "aggregate_type": aggregate.__class__.__name__,
                            "created_at": current_time.isoformat(),
                            "data": aggregate_dict,
                        },
                    )
                )
                await session.execute(stmt)
                await session.commit()
            self.logger.structured_log(
                "DEBUG",
                f"Saved snapshot for aggregate {aggregate.id}",
                name="uno.events.snapshots",
            )
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error saving snapshot: {e}",
                name="uno.events.snapshots",
                error=e,
            )
            raise UnoError.wrap(e, message="Failed to save postgres snapshot")

    async def get_snapshot(self, aggregate_id: str, aggregate_type: type[T]) -> T | None:
        """
        Get a snapshot from PostgreSQL.

        Args:
            aggregate_id: The ID of the aggregate
            aggregate_type: The type of the aggregate

        Returns:
            The snapshot if found and type matches, or None if not found.

        Raises:
            UnoError: If retrieval or deserialization fails.
        """
        try:
            self.logger.structured_log(
                "DEBUG",
                f"Getting snapshot for aggregate {aggregate_id}",
                name="uno.events.snapshots",
            )
            async with self.async_session_factory() as session:
                await self._ensure_table_exists(session)
                query = (
                    select(self.snapshots_table)
                    .where(self.snapshots_table.c.aggregate_id == aggregate_id)
                    .where(self.snapshots_table.c.aggregate_type == aggregate_type.__name__)
                )
                result = await session.execute(query)
                row = result.fetchone()
                if not row:
                    self.logger.structured_log(
                        "DEBUG",
                        f"No snapshot found for aggregate {aggregate_id}",
                        name="uno.events.snapshots",
                    )
                    return None
                aggregate_dict = row.data
                if not hasattr(aggregate_type, "from_dict"):
                    raise UnoError(f"Aggregate type {aggregate_type.__name__} does not implement from_dict method")
                aggregate = aggregate_type.from_dict(aggregate_dict)
                self.logger.structured_log(
                    "DEBUG",
                    f"Retrieved snapshot for aggregate {aggregate_id}",
                    name="uno.events.snapshots",
                )
                return aggregate
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error getting snapshot: {e}",
                name="uno.events.snapshots",
                error=e,
            )
            raise UnoError.wrap(e, message="Failed to get postgres snapshot")

    async def delete_snapshot(self, aggregate_id: str) -> None:
        """
        Delete a snapshot from PostgreSQL.

        Args:
            aggregate_id: The ID of the aggregate

        Raises:
            UnoError: If deletion fails.
        """
        try:
            self.logger.structured_log(
                "DEBUG",
                f"Deleting snapshot for aggregate {aggregate_id}",
                name="uno.events.snapshots",
            )
            async with self.async_session_factory() as session:
                await self._ensure_table_exists(session)
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
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error deleting snapshot: {e}",
                name="uno.events.snapshots",
                error=e,
            )
            raise UnoError.wrap(e, message="Failed to delete postgres snapshot")
