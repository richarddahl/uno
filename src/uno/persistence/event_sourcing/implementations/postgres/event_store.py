# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
PostgreSQL event store implementation.
"""

from __future__ import annotations
from typing import Any, Generic, TypeVar
from datetime import datetime, UTC
from sqlalchemy import Table, Column, String, Integer, JSON, DateTime, MetaData, select

from uno.events.base_event import DomainEvent
from uno.events.protocols import EventStoreProtocol
from uno.events.errors import UnoError
from uno.persistence.sql.config import SQLConfig
from uno.persistence.sql.connection import ConnectionManager
from uno.logging.protocols import LoggerProtocol

E = TypeVar("E", bound=DomainEvent)


class PostgresEventStore(EventStoreProtocol[E], Generic[E]):
    """PostgreSQL event store implementation."""

    def __init__(
        self,
        config: SQLConfig,
        connection_manager: ConnectionManager,
        logger: LoggerProtocol,
    ) -> None:
        """Initialize PostgreSQL event store.

        Args:
            config: SQL configuration
            connection_manager: Connection manager
            logger: Logger service
        """
        self._config = config
        self._connection_manager = connection_manager
        self.logger = logger
        self._metadata = MetaData()
        self._table = self._create_event_table()
        self._ensure_table_exists()

    def _create_event_table(self) -> Table:
        """Create event table definition."""
        return Table(
            "events",
            self._metadata,
            Column("id", String, primary_key=True),
            Column("aggregate_id", String, nullable=False, index=True),
            Column("event_type", String, nullable=False),
            Column("version", Integer, nullable=False),
            Column("payload", JSON, nullable=False),
            Column("created_at", DateTime, nullable=False, default=datetime.now(UTC)),
            Column("event_hash", String, nullable=False),
        )

    async def _ensure_table_exists(self) -> None:
        """Ensure event table exists."""
        try:
            async with self._connection_manager.engine.begin() as conn:
                await conn.run_sync(self._metadata.create_all)
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Failed to create events table: {e}",
                name="uno.events.pgstore",
                error=e,
            )
            raise

    async def save_event(self, event: E) -> None:
        """Save a domain event to the store.

        Args:
            event: The domain event to save

        Raises:
            UnoError: If the event cannot be saved
        """
        try:
            async with self._connection_manager.get_connection() as session:
                stmt = self._table.insert().values(
                    id=event.event_id,
                    aggregate_id=event.aggregate_id,
                    event_type=event.event_type,
                    version=event.version,
                    payload=self._canonical_event_dict(event),
                    event_hash=event.event_hash,
                )
                await session.execute(stmt)
                await session.commit()

            self.logger.structured_log(
                "INFO",
                f"Saved event {event.event_type} for aggregate {event.aggregate_id}",
                name="uno.events.pgstore",
                event_id=event.event_id,
                aggregate_id=event.aggregate_id,
            )
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Failed to save event {event.event_type}: {e}",
                name="uno.events.pgstore",
                error=e,
            )
            raise UnoError(f"Failed to save event {event.event_type}: {e}", error_code="PG_EVENT_STORE_ERROR") from e

    async def get_events(
        self,
        aggregate_id: str | None = None,
        event_type: str | None = None,
        limit: int | None = None,
        since_version: int | None = None,
    ) -> list[E]:
        """Get events by aggregate ID and/or event type.

        Args:
            aggregate_id: The aggregate ID to filter by
            event_type: The event type to filter by
            limit: Maximum number of events to return
            since_version: Return only events since this version

        Returns:
            List of events

        Raises:
            UnoError: If retrieval fails
        """
        try:
            async with self._connection_manager.get_connection() as session:
                stmt = select(self._table)
                if aggregate_id:
                    stmt = stmt.where(self._table.c.aggregate_id == aggregate_id)
                if event_type:
                    stmt = stmt.where(self._table.c.event_type == event_type)
                if since_version is not None:
                    stmt = stmt.where(self._table.c.version >= since_version)
                stmt = stmt.order_by(self._table.c.version)
                if limit:
                    stmt = stmt.limit(limit)

                result = await session.execute(stmt)
                rows = result.fetchall()

                events = []
                for row in rows:
                    event_data = dict(row._mapping["payload"])
                    event_cls = DomainEvent.get_event_class(event_data["event_type"])
                    upcasted = event_cls.upcast(event_data)
                    events.append(upcasted)

            self.logger.structured_log(
                "INFO",
                f"Retrieved {len(events)} events from store",
                name="uno.events.pgstore",
            )
            return events
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Failed to retrieve events: {e}",
                name="uno.events.pgstore",
                error=e,
            )
            raise UnoError(f"Failed to retrieve events: {e}", error_code="PG_EVENT_STORE_ERROR") from e

    async def get_events_by_aggregate_id(
        self, aggregate_id: str, event_types: list[str] | None = None
    ) -> list[E]:
        """Get all events for a specific aggregate ID.

        Args:
            aggregate_id: The ID of the aggregate to get events for
            event_types: Optional list of event types to filter by

        Returns:
            List of events

        Raises:
            UnoError: If retrieval fails
        """
        try:
            async with self._connection_manager.get_connection() as session:
                stmt = select(self._table).where(
                    self._table.c.aggregate_id == aggregate_id
                )
                if event_types:
                    stmt = stmt.where(self._table.c.event_type.in_(event_types))
                stmt = stmt.order_by(self._table.c.version)

                result = await session.execute(stmt)
                rows = result.fetchall()

                events = []
                for row in rows:
                    event_data = dict(row._mapping["payload"])
                    event_cls = DomainEvent.get_event_class(event_data["event_type"])
                    upcasted = event_cls.upcast(event_data)
                    events.append(upcasted)

            self.logger.structured_log(
                "INFO",
                f"Retrieved {len(events)} events for aggregate {aggregate_id}",
                name="uno.events.pgstore",
            )
            return events
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error retrieving events for aggregate {aggregate_id}: {e}",
                name="uno.events.pgstore",
                error=e,
            )
            raise UnoError(f"Error retrieving events for aggregate {aggregate_id}: {e}", error_code="PG_EVENT_STORE_ERROR") from e

    def _canonical_event_dict(self, event: E) -> dict[str, Any]:
        """Convert event to canonical dictionary representation."""
        return event.to_dict()
