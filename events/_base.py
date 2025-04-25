"""
Base interfaces for the event system to avoid circular imports.

This module contains protocol classes and minimal interfaces that are
needed by multiple modules to avoid circular imports.
"""

from typing import Generic, Protocol, TypeVar

from uno.core.domain._base_types import BaseDomainEvent
from uno.core.errors.result import Result

# Define the event type for generics
E = TypeVar('E', bound=BaseDomainEvent)


class EventStoreProtocol(Generic[E], Protocol):
    """
    Protocol for event stores to avoid circular imports.
    
    This protocol defines the minimal interface required by other components 
    without requiring the full EventStore implementation.
    """
    
    async def save_event(self, event: E) -> Result[None, Exception]:
        """Save a domain event to the store."""
        ...
    
    async def get_events(
        self,
        aggregate_id: str | None = None,
        event_type: str | None = None,
        limit: int | None = None,
        since_version: int | None = None,
    ) -> Result[list[E], Exception]:
        """Get events matching criteria."""
        ...
    
    async def get_events_by_aggregate_id(
        self, aggregate_id: str, event_types: list[str] | None = None
    ) -> Result[list[E], Exception]:
        """Get events for a specific aggregate."""
        ...


# Re-export the common types
__all__ = [
    "E",
    "EventStoreProtocol",
]
