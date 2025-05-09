# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
PostgreSQL saga store implementation.
"""

from typing import Any
import asyncpg
import json

from uno.sagas.protocols import SagaStoreProtocol, SagaState


class PostgresSagaStore(SagaStoreProtocol):
    """PostgreSQL implementation of the saga store."""

    def __init__(self, dsn: str) -> None:
        """Initialize the PostgreSQL saga store.

        Args:
            dsn: Database connection string
        """
        self._dsn = dsn
        self._conn: asyncpg.Connection | None = None

    async def connect(self) -> None:
        """Connect to the PostgreSQL database."""
        self._conn = await asyncpg.connect(self._dsn)

    async def save_state(
        self, saga_id: str, saga_type: str, status: str, data: dict[str, Any]
    ) -> None:
        """Save saga state to the database.

        Args:
            saga_id: Unique ID of the saga
            saga_type: Type of the saga
            status: Current status of the saga
            data: Saga state data
        """
        assert self._conn is not None
        await self._conn.execute(
            """
            INSERT INTO uno_sagas (saga_id, saga_type, status, data, updated_at)
            VALUES ($1, $2, $3, $4, now())
            ON CONFLICT (saga_id) DO UPDATE
            SET status = $3, data = $4, updated_at = now()
            """,
            saga_id,
            saga_type,
            status,
            (
                json.dumps(data.to_dict())
                if hasattr(data, "to_dict")
                else json.dumps(data)
            ),
        )

    async def load_state(self, saga_id: str) -> SagaState | None:
        """Load saga state from the database.

        Args:
            saga_id: Unique ID of the saga

        Returns:
            Loaded saga state or None if not found
        """
        assert self._conn is not None
        row = await self._conn.fetchrow(
            "SELECT saga_id, saga_type, status, data FROM uno_sagas WHERE saga_id = $1",
            saga_id,
        )
        if not row:
            return None
        return SagaState(
            saga_id=row["saga_id"],
            saga_type=row["saga_type"],
            status=row["status"],
            data=json.loads(row["data"]),
        )

    async def delete_state(self, saga_id: str) -> None:
        """Delete saga state from the database.

        Args:
            saga_id: Unique ID of the saga to delete
        """
        assert self._conn is not None
        await self._conn.execute("DELETE FROM uno_sagas WHERE saga_id = $1", saga_id)

    async def list_active_sagas(self) -> list[SagaState]:
        """List all active sagas.

        Returns:
            List of active saga states
        """
        assert self._conn is not None
        rows = await self._conn.fetch(
            "SELECT saga_id, saga_type, status, data FROM uno_sagas WHERE status NOT IN ('completed', 'failed', 'approved')"
        )
        return [
            SagaState(
                saga_id=row["saga_id"],
                saga_type=row["saga_type"],
                status=row["status"],
                data=json.loads(row["data"]),
            )
            for row in rows
        ]
