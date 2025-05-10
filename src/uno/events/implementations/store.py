# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
In-memory event store implementation.

This module provides an in-memory implementation of the event store for testing
and simple applications.
"""

import copy
from typing import Any, TypeVar, cast

from uno.events.base_event import DomainEvent
from uno.events.protocols import EventStoreProtocol
from uno.logging.protocols import LoggerProtocol

E = TypeVar("E", bound=DomainEvent)


class InMemoryEventStore(EventStoreProtocol[E]):
    """
    Simple in-memory event store for development and testing.
    Stores events in a Python list grouped by aggregate_id.
    """

    def __init__(self, logger: LoggerProtocol):
        """
        Initialize the in-memory event store.

        Args:
            logger: Logger instance for structured and debug logging.
        """
        self.logger = logger
        self._events: dict[str, list[E]] = {}

    def _canonical_event_dict(self, event: E) -> dict[str, object]:
        """
        Canonical event serialization for storage, logging, and transport.
        Always uses to_dict() for serialization.

        Args:
            event (E): The event to serialize.
        Returns:
            dict[str, object]: The canonically serialized event.
        """
        return event.to_dict()

    async def save_event(self, event: E) -> None:
        """
        Save a domain event to the in-memory store.

        All persisted events are first serialized using the canonical pattern via self._canonical_event_dict(event).
        This guarantees deterministic, tamper-evident storage and transport.

        Args:
            event: The domain event to save

        Raises:
            ValueError: If the event doesn't have an aggregate_id
            Exception: For any other errors during saving
        """
        aggregate_id = getattr(event, "aggregate_id", None)
        if not aggregate_id:
            error = ValueError("Event must have an aggregate_id")
            self.logger.error(
                "Failed to save event",
                event_type=getattr(event, "event_type", type(event).__name__),
                error=str(error),
            )
            raise error

        try:
            if aggregate_id not in self._events:
                self._events[aggregate_id] = []
            # Canonical serialization enforced here
            self._events[aggregate_id].append(copy.deepcopy(event))

            self.logger.info(
                "Saved event",
                event_type=getattr(event, "event_type", type(event).__name__),
                aggregate_id=aggregate_id,
            )
        except Exception as e:
            self.logger.error(
                "Failed to save event",
                event_type=getattr(event, "event_type", type(event).__name__),
                aggregate_id=aggregate_id,
                error=str(e),
            )
            raise

    async def get_events(
        self,
        aggregate_id: str | None = None,
        event_type: str | None = None,
        limit: int | None = None,
        since_version: int | None = None,
    ) -> list[E]:
        """
        Get events by aggregate ID and/or event type.

        Args:
            aggregate_id: The aggregate ID to filter by
            event_type: The event type to filter by
            limit: Maximum number of events to return
            since_version: Return only events since this version

        Returns:
            A list of matching events

        Raises:
            Exception: If there's an error retrieving events
        """
        try:
            result: list[E] = []

            # Handle aggregate_id filter
            if aggregate_id:
                if aggregate_id not in self._events:
                    return []
                events = self._events[aggregate_id]
            else:
                # Flatten all events if no aggregate_id specified
                events = [
                    e for events_list in self._events.values() for e in events_list
                ]

            # Apply remaining filters
            for event in events:
                # Filter by event_type if specified
                if event_type and getattr(event, "event_type", None) != event_type:
                    continue

                # Filter by since_version if specified
                if since_version is not None:
                    event_version = getattr(event, "version", 0)
                    if event_version <= since_version:
                        continue

                result.append(event)

            # Apply limit if specified
            if limit is not None and limit > 0:
                result = result[:limit]

            return result
        except Exception as e:
            self.logger.error(
                "Failed to get events",
                aggregate_id=aggregate_id,
                event_type=event_type,
                error=str(e),
            )
            raise

    async def get_events_by_aggregate_id(
        self, aggregate_id: str, event_types: list[str] | None = None
    ) -> list[E]:
        """
        Get all events for a specific aggregate ID.

        Args:
            aggregate_id: The ID of the aggregate to get events for
            event_types: Optional list of event types to filter by

        Returns:
            A list of matching events

        Raises:
            Exception: If there's an error retrieving events
        """
        try:
            if aggregate_id not in self._events:
                return []

            if not event_types:
                return copy.deepcopy(self._events[aggregate_id])

            # Filter by event types
            filtered_events = [
                e
                for e in self._events[aggregate_id]
                if getattr(e, "event_type", None) in event_types
            ]
            return filtered_events
        except Exception as e:
            self.logger.error(
                "Failed to get events by aggregate ID",
                aggregate_id=aggregate_id,
                event_types=event_types,
                error=str(e),
            )
            raise
