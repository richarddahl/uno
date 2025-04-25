"""
PostgreSQL event store implementation.

This module provides a PostgreSQL-based event store implementation
for the event sourcing system. It uses SQLAlchemy for database operations.
"""

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, TypeVar

from sqlalchemy import TIMESTAMP, Column, MetaData, String, Table, insert, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from uno.core.errors.result import Failure, Result, Success
from uno.core.events._base import E
from uno.core.events.event_store import EventStore
from uno.core.events.events import DomainEvent
from uno.core.logging.logger import LoggerService


class PostgresEventStore(EventStore[E]):
    """
    PostgreSQL implementation of the event store.
    
    This implementation stores events in a PostgreSQL database, providing
    reliable and scalable persistence for domain events.
    """
    
    def __init__(
        self,
        event_type: type[E],
        logger: LoggerService,
        db_session_factory: sessionmaker | None = None,
        table_name: str = "domain_events",
    ):
        """
        Initialize the PostgreSQL event store.
        
        Args:
            event_type: The type of event this store handles
            logger: Logger service for logging
            db_session_factory: Optional factory for creating database sessions
            table_name: Optional name of the table to store events in
        """
        self.event_type = event_type
        self.logger = logger
        self.db_session_factory = db_session_factory
        self.table_name = table_name
        
        # Define the events table schema using SQLAlchemy metadata
        self.metadata = MetaData()
        self.events_table = Table(
            self.table_name,
            self.metadata,
            Column("event_id", String, primary_key=True),
            Column("event_type", String, nullable=False, index=True),
            Column("aggregate_id", String, nullable=False, index=True),
            Column("aggregate_type", String, nullable=False),
            Column("timestamp", TIMESTAMP(timezone=True), nullable=False),
            Column("data", JSONB, nullable=False),
            Column("metadata", JSONB),
        )
    
    async def save_event(self, event: E) -> Result[None, Exception]:
        """
        Save a domain event to the PostgreSQL store.
        
        Args:
            event: The domain event to save
            
        Returns:
            Result with None on success, or an error
        """
        if not hasattr(event, "aggregate_id") or not event.aggregate_id:
            return Failure(ValueError("Event must have an aggregate_id"))
        
        try:
            # Ensure event has a timestamp
            if not hasattr(event, "timestamp") or not event.timestamp:
                # Python 3.9+: event.timestamp = datetime.now(timezone.utc)
                setattr(event, "timestamp", datetime.now(timezone.utc))
            
            # Convert event to dict for storage
            event_dict = {}
            for field in ["event_id", "event_type", "aggregate_id", "aggregate_type", "timestamp"]:
                event_dict[field] = getattr(event, field, None)
            
            # Store event data separately
            event_data = {}
            for attr in dir(event):
                if not attr.startswith("_") and attr not in event_dict:
                    value = getattr(event, attr)
                    if not callable(value):
                        event_data[attr] = value
            
            # Prepare the insert statement
            stmt = insert(self.events_table).values(
                event_id=event_dict["event_id"],
                event_type=event_dict["event_type"],
                aggregate_id=event_dict["aggregate_id"],
                aggregate_type=event_dict["aggregate_type"],
                timestamp=event_dict["timestamp"],
                data=event_data,
                metadata=getattr(event, "metadata", {}),
            )
            
            # Get a database session
            if not self.db_session_factory:
                return Failure(ValueError("Database session factory not provided"))
            
            async with self.db_session_factory() as session:
                await session.execute(stmt)
                await session.commit()
            
            self.logger.structured_log(
                "INFO",
                f"Saved event {event.event_type} for aggregate {event.aggregate_id}",
                name="uno.events.postgres"
            )
            
            return Success(None)
            
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Failed to save event {event.event_type}: {e}",
                name="uno.events.postgres",
                error=e
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
        Get events by aggregate ID and/or event type.
        
        Args:
            aggregate_id: The aggregate ID to filter by
            event_type: The event type to filter by
            limit: Maximum number of events to return
            since_version: Return only events since this version
            
        Returns:
            Result with a list of events or an error
        """
        try:
            # Build the query
            query = select(self.events_table)
            
            # Apply filters
            if aggregate_id:
                query = query.where(self.events_table.c.aggregate_id == aggregate_id)
            
            if event_type:
                query = query.where(self.events_table.c.event_type == event_type)
            
            # Order by timestamp
            query = query.order_by(self.events_table.c.timestamp)
            
            # Apply limit
            if limit:
                query = query.limit(limit)
            
            # Get a database session
            if not self.db_session_factory:
                return Failure(ValueError("Database session factory not provided"))
            
            async with self.db_session_factory() as session:
                result = await session.execute(query)
                rows = result.mappings().all()
            
            # Convert rows to domain events
            events = []
            for row in rows:
                # Skip based on version if needed
                if since_version is not None and row.get("version", 0) < since_version:
                    continue
                
                # Create a new event instance
                event = self._row_to_event(row)
                events.append(event)
            
            self.logger.structured_log(
                "INFO",
                f"Retrieved {len(events)} events from store",
                name="uno.events.postgres"
            )
            
            return Success(events)
            
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Failed to retrieve events: {e}",
                name="uno.events.postgres",
                error=e
            )
            return Failure(e)
    
    async def get_events_by_aggregate_id(
        self, aggregate_id: str, event_types: list[str] | None = None
    ) -> Result[list[E], Exception]:
        """
        Get all events for a specific aggregate ID.
        
        Args:
            aggregate_id: The ID of the aggregate to get events for
            event_types: Optional list of event types to filter by
            
        Returns:
            Result with a list of events or an error
        """
        try:
            # Build the query
            query = select(self.events_table).where(
                self.events_table.c.aggregate_id == aggregate_id
            )
            
            # Filter by event types if provided
            if event_types:
                query = query.where(self.events_table.c.event_type.in_(event_types))
            
            # Order by timestamp
            query = query.order_by(self.events_table.c.timestamp)
            
            # Get a database session
            if not self.db_session_factory:
                return Failure(ValueError("Database session factory not provided"))
            
            async with self.db_session_factory() as session:
                result = await session.execute(query)
                rows = result.mappings().all()
            
            # Convert rows to domain events
            events = [self._row_to_event(row) for row in rows]
            
            self.logger.structured_log(
                "INFO",
                f"Retrieved {len(events)} events for aggregate {aggregate_id}",
                name="uno.events.postgres"
            )
            
            return Success(events)
            
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error retrieving events for aggregate {aggregate_id}: {e}",
                name="uno.events.postgres",
                error=e
            )
            return Failure(e)
    
    def _row_to_event(self, row: dict[str, Any]) -> E:
        """
        Convert a database row to a domain event.
        
        Args:
            row: The database row to convert
            
        Returns:
            A domain event instance
        """
        # Extract base fields from the row
        event_id = row.get("event_id")
        event_type = row.get("event_type")
        aggregate_id = row.get("aggregate_id")
        aggregate_type = row.get("aggregate_type")
        timestamp = row.get("timestamp")
        data = row.get("data", {})
        metadata = row.get("metadata", {})
        
        # Create event instance
        event = self.event_type(
            event_id=event_id,
            event_type=event_type,
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
        )
        
        # Set timestamp
        if timestamp:
            setattr(event, "timestamp", timestamp)
        
        # Set data fields
        for key, value in data.items():
            if not key.startswith("_") and hasattr(event, key):
                setattr(event, key, value)
        
        # Set metadata
        if hasattr(event, "metadata"):
            setattr(event, "metadata", metadata)
        
        return event
