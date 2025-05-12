"""PostgreSQL-based implementation of snapshot storage."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import asyncpg

from uno.snapshots.protocols import SnapshotProtocol


class PostgresSnapshot:
    """PostgreSQL implementation of a snapshot."""

    def __init__(
        self,
        aggregate_id: str,
        aggregate_version: int,
        created_at: datetime,
        state: dict[str, Any],
    ) -> None:
        """
        Initialize a PostgreSQL snapshot.

        Args:
            aggregate_id: The ID of the aggregate
            aggregate_version: The version of the aggregate
            created_at: When the snapshot was created
            state: The serialized state of the aggregate
        """
        self.aggregate_id = aggregate_id
        self.aggregate_version = aggregate_version
        self.created_at = created_at
        self.state = state


class PostgresSnapshotStore:
    """PostgreSQL implementation of snapshot storage."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        """
        Initialize the PostgreSQL snapshot store.

        Args:
            pool: Connection pool for PostgreSQL
        """
        self.pool = pool

    async def initialize(self) -> None:
        """Initialize the database schema for snapshots."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    id SERIAL PRIMARY KEY,
                    aggregate_id TEXT NOT NULL,
                    aggregate_version INTEGER NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    state JSONB NOT NULL,
                    UNIQUE(aggregate_id, aggregate_version)
                );
                
                CREATE INDEX IF NOT EXISTS snapshots_aggregate_id_idx ON snapshots(aggregate_id);
                CREATE INDEX IF NOT EXISTS snapshots_aggregate_version_idx ON snapshots(aggregate_version);
            """
            )

    async def save_snapshot(
        self, aggregate_id: str, aggregate_version: int, state: dict[str, Any]
    ) -> None:
        """
        Save a snapshot to PostgreSQL storage.

        Args:
            aggregate_id: The ID of the aggregate
            aggregate_version: The version of the aggregate
            state: The serialized state of the aggregate
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO snapshots (aggregate_id, aggregate_version, state)
                VALUES ($1, $2, $3)
                ON CONFLICT (aggregate_id, aggregate_version)
                DO UPDATE SET state = $3, created_at = NOW()
            """,
                aggregate_id,
                aggregate_version,
                state,
            )

    async def get_latest_snapshot(self, aggregate_id: str) -> SnapshotProtocol | None:
        """
        Get the latest snapshot for an aggregate from PostgreSQL storage.

        Args:
            aggregate_id: The ID of the aggregate

        Returns:
            SnapshotProtocol | None: The latest snapshot if available, None otherwise
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT aggregate_id, aggregate_version, created_at, state
                FROM snapshots
                WHERE aggregate_id = $1
                ORDER BY aggregate_version DESC
                LIMIT 1
            """,
                aggregate_id,
            )

            if not row:
                return None

            return PostgresSnapshot(
                aggregate_id=row["aggregate_id"],
                aggregate_version=row["aggregate_version"],
                created_at=row["created_at"],
                state=row["state"],
            )

    async def delete_snapshots(self, aggregate_id: str) -> None:
        """
        Delete all snapshots for an aggregate from PostgreSQL storage.

        Args:
            aggregate_id: The ID of the aggregate
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM snapshots
                WHERE aggregate_id = $1
            """,
                aggregate_id,
            )
