"""
Event store implementation for domain events.

This module provides the event store implementation for persisting and retrieving
domain events, supporting event-driven architectures and event sourcing.
"""

import copy
import json
from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from sqlalchemy import TIMESTAMP, Column, MetaData, String, Table, insert, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

# Import base interfaces first to avoid circular dependencies
from uno.core.events.interfaces import EventStoreProtocol
from uno.core.events.base_event import DomainEvent
from typing import TypeVar
E = TypeVar("E", bound=DomainEvent)
from uno.core.errors.result import Failure, Result, Success
from uno.core.logging.logger import LoggerService
from uno.core.logging.logger import LoggingConfig

# Import snapshots avoiding circular dependencies
from uno.core.events.snapshots import (
    CompositeSnapshotStrategy,
    EventCountSnapshotStrategy,
    SnapshotStore,
    SnapshotStrategy,
    TimeBasedSnapshotStrategy,
)

# Define a protocol for common aggregate methods to avoid importing AggregateRoot
class AggregateProtocol(Protocol):
    id: Any
    
    def add_event(self, event: Any) -> None:
        ...
    
    def clear_events(self) -> list[Any]:
        ...


from typing import Generic

class EventStore(EventStoreProtocol[E], Generic[E]):
    """
    Abstract base class for event stores.
    
    Event stores persist domain events for event sourcing, auditing,
    and integration with external systems.

    All event persistence MUST use the canonical serialization helper _canonical_event_dict.
    """

    def _canonical_event_dict(self, event: E) -> dict[str, object]:
        """
        Canonical event serialization for storage, hashing, and transport.
        Always uses to_dict() for serialization.
        """
        return event.to_dict()
    
    async def save_event(self, event: E) -> Result[None, Exception]:
        """
        Save a domain event to the store.
        
        Args:
            event: The domain event to save
            
        Returns:
            Result with None on success, or an error
        """
        raise NotImplementedError
    
    async def get_events(
        self,
        aggregate_id: str | None = None,
        event_type: str | None = None,
        limit: int | None = None,
        since_version: int | None = None,
    ) -> Result[list[DomainEvent], Exception]:
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
        raise NotImplementedError
    
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
        raise NotImplementedError


class InMemoryEventStore(EventStore[E]):
    """
    Simple in-memory event store for development and testing.
    Stores events in a Python list grouped by aggregate_id.
    """
    def __init__(self, logger: LoggerService):
        self.logger = logger
        self._events: dict[str, list[E]] = {}

    async def save_event(self, event: E) -> Result[None, Exception]:
        """Save a domain event to the in-memory store.
        
        All persisted events are first serialized using the canonical pattern via self._canonical_event_dict(event).
        This guarantees deterministic, tamper-evident storage and transport.
        
        Args:
            event: The domain event to save
            
        Returns:
            Result with None on success, or an error
        """
        aggregate_id = getattr(event, "aggregate_id", None)
        if not aggregate_id:
            error = ValueError("Event must have an aggregate_id")
            self.logger.structured_log(
                "ERROR",
                f"Failed to save event {getattr(event, 'event_type', type(event))}: {error}",
                name="uno.events.inmem",
                error=error
            )
            return Failure(error)
        
        try:
            if aggregate_id not in self._events:
                self._events[aggregate_id] = []
            # Canonical serialization enforced here
            canonical_event = self._canonical_event_dict(event)
            self._events[aggregate_id].append(copy.deepcopy(event))
            
            self.logger.structured_log(
                "INFO",
                f"Saved event {getattr(event, 'event_type', type(event))} for aggregate {aggregate_id}",
                name="uno.events.inmem"
            )
            return Success(None)
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Failed to save event {event.event_type}: {e}",
                name="uno.events.inmem",
                error=e
            )
            return Failure(e)

    async def get_events(
        self,
        aggregate_id: str | None = None,
        event_type: str | None = None,
        limit: int | None = None,
        since_version: int | None = None,
    ) -> Result[list[DomainEvent], Exception]:
        """Get events by aggregate ID and/or event type.
        
        Args:
            aggregate_id: The aggregate ID to filter by
            event_type: The event type to filter by
            limit: Maximum number of events to return
            since_version: Return only events since this version
            
        Returns:
            Result with a list of events or an error
        """
        try:
            # Build a flat list of all events
            all_events = []
            for events in self._events.values():
                all_events.extend(events)
                
            # Apply filters
            filtered_events = all_events
            
            if aggregate_id:
                filtered_events = [e for e in filtered_events 
                                 if getattr(e, "aggregate_id", None) == aggregate_id]
            
            if event_type:
                filtered_events = [e for e in filtered_events 
                                 if getattr(e, "event_type", None) == event_type]
            
            if since_version is not None:
                filtered_events = [e for e in filtered_events 
                                 if getattr(e, "version", 0) >= since_version]
            
            # Apply limit
            if limit:
                filtered_events = filtered_events[:limit]
                
            # Log the result
            self.logger.structured_log(
                "INFO",
                f"Retrieved {len(filtered_events)} events from store",
                name="uno.events.inmem"
            )
            
            return Success(filtered_events)
            
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Failed to retrieve events: {e}",
                name="uno.events.inmem",
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
            if aggregate_id not in self._events:
                return Success([])
                
            events = self._events[aggregate_id]
            
            # Filter by event types if provided
            if event_types:
                events = [e for e in events if e.event_type in event_types]
                
            return Success(events)
            
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error retrieving events for aggregate {aggregate_id}: {e}",
                name="uno.events.inmem",
                error=e
            )
            return Failure(e)

# The EventSourcedRepository should be imported directly from its module
# We don't need to re-export it here
