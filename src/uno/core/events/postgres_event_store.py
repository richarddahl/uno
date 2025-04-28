"""
Production-grade Postgres event store for Uno framework.
Implements canonical event persistence, replay, and concurrency control.
"""

from typing import Any, Callable, TypeVar, Generic, cast
from uuid import uuid4
from datetime import datetime, UTC
from uno.core.events.event_store import EventStore
from uno.core.events.base_event import DomainEvent
from uno.core.errors.result import Result, Success, Failure
from uno.core.logging.logger import LoggerService, LoggingConfig
from sqlalchemy import text, select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy import Table, Column, String, Integer, TIMESTAMP, MetaData
import sqlalchemy as sa
from uno.core.di import get_service_provider


E = TypeVar("E", bound=DomainEvent)

class PostgresEventStore(EventStore[E], Generic[E]):
    """
    Production-grade Postgres event store for Uno.
    Implements canonical event persistence, replay, and concurrency control.
    """
    def __init__(
        self,
        db_session: AsyncSession | None = None,
        logger_factory: Callable[..., LoggerService] | None = None,
        event_table: str = "uno_events",
    ):
        if db_session is None:
            db_session = get_service_provider().get_service("db_session")
        self.db_session = db_session
        self.table_name = event_table
        self.metadata = MetaData()
        self.table = Table(
            self.table_name,
            self.metadata,
            Column("id", String, primary_key=True),
            Column("aggregate_id", String, index=True, nullable=False),
            Column("event_type", String, index=True, nullable=False),
            Column("version", Integer, index=True, nullable=False),
            Column("timestamp", TIMESTAMP, nullable=False),
            Column("payload", JSONB, nullable=False),
            sa.UniqueConstraint("aggregate_id", "version", name=f"uq_{self.table_name}_agg_ver"),
        )
        if logger_factory:
            self.logger = logger_factory("eventstore_postgres")
        else:
            self.logger = LoggerService(LoggingConfig())

    async def save_event(self, event: E) -> Result[None, Exception]:
        """
        Save a domain event to Postgres with concurrency/version check.
        """
        try:
            async with self.db_session as session:
                async with session.begin():
                    payload = self._canonical_event_dict(event)
                    aggregate_id = getattr(event, "aggregate_id", None)
                    version = getattr(event, "version", None)
                    event_type = getattr(event, "event_type", None)
                    if not aggregate_id or version is None or not event_type:
                        raise ValueError("Event must have aggregate_id, version, event_type")
                    row = {
                        "id": str(uuid4()),
                        "aggregate_id": aggregate_id,
                        "event_type": event_type,
                        "version": version,
                        "timestamp": getattr(event, "timestamp", datetime.now(UTC)),
                        "payload": payload,
                    }
                    stmt = insert(self.table).values(**row)
                    await session.execute(stmt)
            self.logger.structured_log(
                "INFO",
                f"Saved event {event_type} v{version} for aggregate {aggregate_id}",
                name="uno.events.pgstore",
            )
            return Success(None)
        except IntegrityError as e:
            self.logger.structured_log(
                "ERROR",
                f"Concurrency/version conflict for aggregate {aggregate_id} v{version}: {e}",
                name="uno.events.pgstore",
                error=e,
            )
            return Failure(e)
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Failed to save event: {e}",
                name="uno.events.pgstore",
                error=e,
            )
            return Failure(e)

    async def get_events(
        self,
        aggregate_id: str | None = None,
        event_type: str | None = None,
        limit: int | None = None,
        since_version: int | None = None,
    ) -> Result[list[E], Exception]:
        """
        Get events by aggregate ID and/or event type, with optional limit and version filter.
        """
        try:
            async with self.db_session as session:
                stmt = select(self.table)
                if aggregate_id:
                    stmt = stmt.where(self.table.c.aggregate_id == aggregate_id)
                if event_type:
                    stmt = stmt.where(self.table.c.event_type == event_type)
                if since_version is not None:
                    stmt = stmt.where(self.table.c.version >= since_version)
                stmt = stmt.order_by(self.table.c.version)
                if limit:
                    stmt = stmt.limit(limit)
                rows = (await session.execute(stmt)).fetchall()
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
            return Success(events)
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Failed to retrieve events: {e}",
                name="uno.events.pgstore",
                error=e,
            )
            return Failure(e)

    async def get_events_by_aggregate_id(
        self, aggregate_id: str, event_types: list[str] | None = None
    ) -> Result[list[E], Exception]:
        """
        Get all events for a specific aggregate ID, optionally filtered by event types.
        """
        try:
            async with self.db_session as session:
                stmt = select(self.table).where(self.table.c.aggregate_id == aggregate_id)
                if event_types:
                    stmt = stmt.where(self.table.c.event_type.in_(event_types))
                stmt = stmt.order_by(self.table.c.version)
                rows = (await session.execute(stmt)).fetchall()
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
            return Success(events)
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error retrieving events for aggregate {aggregate_id}: {e}",
                name="uno.events.pgstore",
                error=e,
            )
            return Failure(e)
