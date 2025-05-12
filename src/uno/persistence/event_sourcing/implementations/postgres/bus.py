# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
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
from typing import Any, TypeVar

from uno.events.protocols import EventBusProtocol
from uno.events.base_event import DomainEvent
from uno.events.errors import EventPublishError

E = TypeVar("E", bound=DomainEvent)


class PostgresBus:
    """Base class for PostgreSQL-backed message buses."""

    def __init__(self, dsn: str, channel: str, table: str) -> None:
        """Initialize PostgreSQL bus.

        Args:
            dsn: Database connection string
            channel: Postgres notification channel
            table: Table to store messages
        """
        self._dsn = dsn
        self._channel = channel
        self._table = table
        self._listeners: list[Callable[[dict[str, Any]], Awaitable[None]]] = []
        self._conn: asyncpg.Connection | None = None

    async def connect(self) -> None:
        """Connect to the PostgreSQL database and start listening for notifications."""
        self._conn = await asyncpg.connect(self._dsn)
        await self._conn.execute(f"LISTEN {self._channel}")
        asyncio.create_task(self._listen_loop())

    async def publish(self, payload: dict[str, Any]) -> None:
        """Publish a message to the bus.

        Args:
            payload: Message payload

        Raises:
            Exception: If there's an error publishing the message
        """
        try:
            assert self._conn is not None
            if hasattr(payload, "model_dump"):
                data = json.dumps(
                    payload.model_dump(
                        mode="json",
                        by_alias=True,
                        exclude_unset=True,
                        exclude_none=True,
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
        except Exception as e:
            raise Exception(f"Failed to publish message: {e}") from e

    def subscribe(self, handler: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
        """Subscribe to messages on this bus.

        Args:
            handler: Callback function to invoke when messages are received
        """
        self._listeners.append(handler)

    async def _listen_loop(self) -> None:
        """Listen for PostgreSQL notifications and process messages."""
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


class PostgresEventBus(PostgresBus, EventBusProtocol):
    """PostgreSQL-backed event bus implementation."""

    def __init__(self, dsn: str) -> None:
        """Initialize PostgreSQL event bus.

        Args:
            dsn: Database connection string
        """
        super().__init__(dsn, channel="uno_events", table="uno_events")

    async def publish(self, event: E, metadata: dict[str, Any] | None = None) -> None:
        """Publish an event to the bus.

        Args:
            event: Domain event to publish
            metadata: Optional metadata to include with the event

        Raises:
            EventPublishError: If there's an error publishing the event
        """
        try:
            payload = self._prepare_event_payload(event, metadata)
            await super().publish(payload)
        except Exception as e:
            event_type = getattr(event, "event_type", type(event).__name__)
            raise EventPublishError(event_type=event_type, reason=str(e)) from e

    async def publish_many(
        self, events: list[E], batch_size: int | None = None
    ) -> None:
        """Publish multiple events to the bus in batches and concurrently.

        Args:
            events: List of domain events to publish
            batch_size: Number of events to process concurrently in a batch
        Raises:
            EventPublishError: If there's an error publishing any event
        """
        batch_size = batch_size or 10
        for i in range(0, len(events), batch_size):
            batch = events[i : i + batch_size]
            tasks = [self.publish(event) for event in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    raise EventPublishError(
                        event_type="batch", reason=str(result)
                    ) from result

    def _prepare_event_payload(
        self, event: E, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Prepare event payload for publishing.

        Args:
            event: Domain event
            metadata: Optional metadata

        Returns:
            Dictionary representation of the event with metadata
        """
        if hasattr(event, "model_dump"):
            payload = event.model_dump(
                mode="json", by_alias=True, exclude_unset=True, exclude_none=True
            )
        elif hasattr(event, "to_dict"):
            payload = event.to_dict()
        else:
            payload = event.__dict__.copy()

        if metadata:
            payload["metadata"] = metadata

        return payload


class PostgresCommandBus(PostgresBus):
    """PostgreSQL-backed command bus implementation."""

    def __init__(self, dsn: str) -> None:
        """Initialize PostgreSQL command bus.

        Args:
            dsn: Database connection string
        """
        super().__init__(dsn, channel="uno_commands", table="uno_commands")
