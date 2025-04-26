"""
Event-sourced repository for Uno DDD aggregates.

This module provides a generic, DI-ready repository that persists and rehydrates aggregates
using the event sourcing pattern. Integrates with Uno's DI, logging, error, and config systems.
"""

from typing import Generic, TypeVar, cast

from uno.core.di.decorators import framework_service
from uno.core.domain.core import AggregateRoot
from uno.core.domain.repository import Repository
from uno.core.events._base import EventStoreProtocol  # Avoid circular dependencies
from uno.core.events.events import EventPublisherProtocol
from uno.core.logging.logger import LoggerService

T = TypeVar("T", bound=AggregateRoot)

@framework_service(service_type=Repository)
class EventSourcedRepository(Generic[T], Repository[T]):
    """
    Repository implementation that uses event sourcing for aggregate persistence.

    Loads aggregates by replaying events from the event store, and saves aggregates
    by persisting new events and publishing them via the event bus/publisher.
    All dependencies are injected via Uno DI. For configuration, inject a specific config class or use uno.core.config.get_config as needed.
    """
    def __init__(
        self,
        aggregate_type: type[T],
        event_store: EventStoreProtocol,
        event_publisher: EventPublisherProtocol,
        logger: LoggerService,

    ):
        self.aggregate_type = aggregate_type
        self.event_store = event_store
        self.event_publisher = event_publisher
        self.logger = logger

    async def get_by_id(self, id: str) -> T | None:
        """
        Load an aggregate by ID by replaying its event stream.
        """
        events = await self.event_store.get_events_by_aggregate_id(id)
        if not events:
            return None
        aggregate = self.aggregate_type.from_events(events)
        return cast("T", aggregate)

    async def list(self) -> list[T]:
        """
        List all aggregates of this type (inefficient; for demo/testing only).
        """
        # This is a placeholder; in production, use a projection/read model
        all_events = await self.event_store.get_events_by_type(self.aggregate_type.__name__)
        aggregates = {}
        for event in all_events:
            if event.aggregate_id not in aggregates:
                aggregates[event.aggregate_id] = []
            aggregates[event.aggregate_id].append(event)
        return [self.aggregate_type.from_events(evts) for evts in aggregates.values()]

    async def add(self, entity: T) -> None:
        """
        Persist new events from the aggregate and publish them.
        """
        new_events = entity.clear_events()
        for event in new_events:
            await self.event_store.save_event(event)
            await self.event_publisher.publish(event)
        self.logger.info(f"Aggregate {entity.id} persisted with {len(new_events)} new events.")

    async def remove(self, id: str) -> None:
        """
        Remove an aggregate by ID (typically by appending a deletion event).
        """
        # Domain-specific: could append a 'deleted' event
        self.logger.info(f"Aggregate {id} removal requested (event sourcing: soft delete)")
        # Not implemented: see event sourcing best practices
