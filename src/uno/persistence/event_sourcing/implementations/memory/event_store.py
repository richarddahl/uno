# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
In-memory event store implementation.

This module provides an in-memory implementation of the event store for development
and testing purposes. It stores events in memory and provides methods to save and
retrieve events by aggregate ID.
"""

import copy
from collections.abc import Sequence
from typing import TypeVar, TYPE_CHECKING, Any, cast

from uno.events.base import DomainEvent

if TYPE_CHECKING:
    from uno.logging.protocols import LoggerProtocol

E = TypeVar("E", bound=DomainEvent)


class InMemoryEventStore:
    """
    Simple in-memory event store for development and testing.

    Stores events in a Python dictionary grouped by aggregate_id.

    This implementation is intended for development and testing only.
    For production use, consider a persistent implementation like
    PostgresEventStore.
    """

    def __init__(self, logger: "LoggerProtocol") -> None:
        """
        Initialize the in-memory event store.

        Args:
            logger: Logger instance for structured and debug logging.
        """
        self.logger = logger
        self._events: dict[str, list[E]] = {}

    def _canonical_event_dict(self, event: E) -> dict[str, Any]:
        """
        Canonical event serialization for storage, logging, and transport.

        Args:
            event: The event to serialize.
        Returns:
            The canonically serialized event.
        """
        if hasattr(event, "model_dump"):
            return dict(
                event.model_dump(exclude_none=True, exclude_unset=True, by_alias=True)
            )
        elif hasattr(event, "to_dict"):
            return event.to_dict()
        return dict(event.__dict__)

    async def save_event(self, event: E) -> None:
        """
        Save an event to the store.

        Args:
            event: The event to save.
        """
        # Get the aggregate ID from the event
        aggregate_id = getattr(event, "aggregate_id", None)
        if not aggregate_id:
            await self.logger.warning(
                "Event has no aggregate_id, using event_id instead",
                event_type=event.__class__.__name__,
                event_id=getattr(event, "event_id", None),
            )
            aggregate_id = getattr(event, "event_id", "unknown")

        # Initialize the list for this aggregate if it doesn't exist
        if aggregate_id not in self._events:
            self._events[aggregate_id] = []

        # Log the event being saved
        await self.logger.debug(
            "Saving event",
            event_type=event.__class__.__name__,
            event_id=getattr(event, "event_id", None),
            aggregate_id=aggregate_id,
            event=self._canonical_event_dict(event),
        )

        # Add the event to the store
        self._events[aggregate_id].append(event)

    async def get_events_for_aggregate(self, aggregate_id: str) -> Sequence[E]:
        """
        Get all events for a specific aggregate.

        Args:
            aggregate_id: The ID of the aggregate to get events for.

        Returns:
            A sequence of events for the specified aggregate.
        """
        events = self._events.get(aggregate_id, [])

        # Log retrieval
        await self.logger.debug(
            "Retrieved events for aggregate",
            aggregate_id=aggregate_id,
            event_count=len(events),
        )

        # Return a copy to prevent mutation
        return cast(Sequence[E], copy.deepcopy(events))

    async def get_all_events(self) -> Sequence[E]:
        """
        Get all events from the store.

        Returns:
            A sequence of all events in the store.
        """
        all_events: list[E] = []
        for events in self._events.values():
            all_events.extend(events)

        # Sort by sequence number if available
        all_events.sort(
            key=lambda e: getattr(e, "sequence_number", getattr(e, "timestamp", 0))
        )

        # Log retrieval
        await self.logger.debug("Retrieved all events", event_count=len(all_events))

        return cast(Sequence[E], copy.deepcopy(all_events))

    async def clear(self) -> None:
        """
        Clear all events from the store.
        Useful for testing.
        """
        event_count = sum(len(events) for events in self._events.values())
        self._events.clear()

        await self.logger.info("Cleared event store", cleared_event_count=event_count)


__all__ = ["InMemoryEventStore"]
