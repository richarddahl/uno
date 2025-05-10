"""
Postgres-backed EventBus and CommandBus for Uno using asyncpg.
- Publishes events/commands by inserting into a table and issuing NOTIFY.
- Listeners use LISTEN to get notified and then fetch new events/commands from the table.
- Ensures durability and real-time delivery (best effort).
"""

import asyncio
import asyncpg
import json
from collections.abc import Awaitable, Callable
from typing import Any


class PostgresBus:
    def __init__(self, dsn: str, channel: str, table: str) -> None:
        self._dsn = dsn
        self._channel = channel
        self._table = table
        self._listeners: list[Callable[[dict[str, Any]], Awaitable[None]]] = []
        self._conn: asyncpg.Connection | None = None

    async def connect(self) -> None:
        self._conn = await asyncpg.connect(self._dsn)
        await self._conn.execute(f"LISTEN {self._channel}")
        asyncio.create_task(self._listen_loop())

    async def publish(self, payload: dict[str, Any]) -> None:
        assert self._conn is not None
        if hasattr(payload, "model_dump"):
            data = json.dumps(
                payload.model_dump(
                    mode="json", by_alias=True, exclude_unset=True, exclude_none=True
                )
            )
        else:
            data = json.dumps(payload)
        await self._conn.execute(
            f"""
            INSERT INTO {self._table} (payload) VALUES ($1)
        """,
            data,
        )
        await self._conn.execute(f"NOTIFY {self._channel}")

    def subscribe(self, handler: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
        self._listeners.append(handler)

    async def _listen_loop(self) -> None:
        assert self._conn is not None
        while True:
            msg = await self._conn.connection.notifies.get()
            # Fetch all new rows from table
            rows = await self._conn.fetch(
                f"SELECT id, payload FROM {self._table} WHERE processed = FALSE ORDER BY id"
            )
            for row in rows:
                payload = json.loads(row["payload"])
                for handler in self._listeners:
                    await handler(payload)
                await self._conn.execute(
                    f"UPDATE {self._table} SET processed = TRUE WHERE id = $1",
                    row["id"],
                )


class PostgresEventBus(PostgresBus):
    def __init__(self, dsn: str) -> None:
        super().__init__(dsn, channel="uno_events", table="uno_events")


class PostgresCommandBus(PostgresBus):
    def __init__(self, dsn: str) -> None:
        super().__init__(dsn, channel="uno_commands", table="uno_commands")
