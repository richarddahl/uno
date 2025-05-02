"""
PostgresSagaStore: Durable saga state store for Uno using asyncpg.
"""
from typing import Any
import asyncpg
import json
from uno.core.events.saga_store import SagaStore, SagaState

class PostgresSagaStore(SagaStore):
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._conn: asyncpg.Connection | None = None

    async def connect(self) -> None:
        self._conn = await asyncpg.connect(self._dsn)

    async def save_state(self, saga_id: str, saga_type: str, status: str, data: dict[str, Any]) -> None:
        assert self._conn is not None
        await self._conn.execute(
            """
            INSERT INTO uno_sagas (saga_id, saga_type, status, data, updated_at)
            VALUES ($1, $2, $3, $4, now())
            ON CONFLICT (saga_id) DO UPDATE
            SET status = $3, data = $4, updated_at = now()
            """,
            saga_id, saga_type, status, (
                json.dumps(data.to_dict()) if hasattr(data, "to_dict") else json.dumps(data)
            )
        )

    async def load_state(self, saga_id: str) -> SagaState | None:
        assert self._conn is not None
        row = await self._conn.fetchrow(
            "SELECT saga_id, saga_type, status, data FROM uno_sagas WHERE saga_id = $1",
            saga_id
        )
        if not row:
            return None
        return SagaState(
            saga_id=row["saga_id"],
            saga_type=row["saga_type"],
            status=row["status"],
            data=json.loads(row["data"])
        )

    async def delete_state(self, saga_id: str) -> None:
        assert self._conn is not None
        await self._conn.execute("DELETE FROM uno_sagas WHERE saga_id = $1", saga_id)

    async def list_active_sagas(self) -> list[SagaState]:
        assert self._conn is not None
        rows = await self._conn.fetch(
            "SELECT saga_id, saga_type, status, data FROM uno_sagas WHERE status NOT IN ('completed', 'failed', 'approved')"
        )
        return [SagaState(
            saga_id=row["saga_id"],
            saga_type=row["saga_type"],
            status=row["status"],
            data=json.loads(row["data"])
        ) for row in rows]
