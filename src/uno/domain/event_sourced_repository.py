"""
Event-sourced repository for Uno DDD aggregates.

This module provides a generic, DI-ready repository that persists and rehydrates aggregates
using the event sourcing pattern. Integrates with Uno's DI, logging, error, and config systems.
"""

from typing import Generic, TypeVar
from uno.di.decorators import framework_service
from uno.domain.aggregate import AggregateRoot
from uno.domain.repository import Repository
from uno.events.event_store import EventStoreProtocol
from uno.events.publisher import EventPublisherProtocol
from uno.errors.result import Result, Success, Failure
from uno.events.deleted_event import DeletedEvent
from uno.infrastructure.logging.logger import LoggerService

T = TypeVar("T", bound=AggregateRoot)


@framework_service(service_type=Repository)
class EventSourcedRepository(Generic[T], Repository[T]):
    """
    Repository implementation that uses event sourcing for aggregate persistence.

    Loads aggregates by replaying events from the event store, and saves aggregates
    by persisting new events and publishing them via the event bus/publisher.
    All dependencies are injected via Uno DI. For configuration, inject a specific config class or use uno.infrastructure.config.get_config as needed.
    """

    def __init__(
        self,
        aggregate_type: type[T],
        event_store: EventStoreProtocol,
        event_publisher: EventPublisherProtocol,
        logger: LoggerService,
    ):
        """
        DI-injected repository for event-sourced aggregates.
        Args:
            aggregate_type: The aggregate root type
            event_store: The event store implementation
            event_publisher: The event publisher/bus
            logger: LoggerService for structured logging
        """
        self.aggregate_type = aggregate_type
        self.event_store = event_store
        self.event_publisher = event_publisher
        self.logger = logger

    async def get_by_id(self, id: str) -> Result[T | None, Exception]:
        """
        Load an aggregate by ID by replaying its event stream.
        Returns:
            Success(aggregate) if found, Success(None) if not found, or Failure(error)
        """
        try:
            events_result = await self.event_store.get_events_by_aggregate_id(id)
            if not events_result.is_success:
                self.logger.structured_log(
                    "ERROR",
                    f"Failed to load events for aggregate {id}",
                    aggregate_id=id,
                    error=events_result.error,
                )
                return Failure(events_result.error)
            events = events_result.value
            if not events:
                return Success(None)
            aggregate = self.aggregate_type.from_events(events)
            return Success(aggregate)
        except Exception as exc:
            self.logger.structured_log(
                "ERROR",
                f"Exception loading aggregate {id}",
                aggregate_id=id,
                exc_info=exc,
            )
            return Failure(exc)

    async def list(self) -> Result[list[T], Exception]:
        """
        List all aggregates of this type (inefficient; for demo/testing only).
        Returns:
            Success(list of aggregates) or Failure(error)
        """
        try:
            events_result = await self.event_store.get_events_by_type(
                self.aggregate_type.__name__
            )
            if not events_result.is_success:
                self.logger.structured_log(
                    "ERROR",
                    f"Failed to load events for aggregate type {self.aggregate_type.__name__}",
                    error=events_result.error,
                )
                return Failure(events_result.error)
            all_events = events_result.value
            aggregates: dict[str, list] = {}
            for event in all_events:
                aggregates.setdefault(event.aggregate_id, []).append(event)
            result = [
                self.aggregate_type.from_events(evts) for evts in aggregates.values()
            ]
            return Success(result)
        except Exception as exc:
            self.logger.structured_log(
                "ERROR",
                f"Exception listing aggregates for {self.aggregate_type.__name__}",
                exc_info=exc,
            )
            return Failure(exc)

    async def add(self, entity: T) -> Result[None, Exception]:
        """
        Persist new events from the aggregate and publish them.
        Returns:
            Success(None) on success, Failure(error) on error
        """
        try:
            new_events = entity.clear_events()
            for event in new_events:
                # Ensure event_hash is set before saving or publishing
                event.set_event_hash()  # TODO: inject hash_service if/when needed
                save_result = await self.event_store.save_event(event)
                if not save_result.is_success:
                    self.logger.structured_log(
                        "ERROR",
                        f"Failed to save event {event.event_type}",
                        event_id=event.event_id,
                        aggregate_id=event.aggregate_id,
                        error=save_result.error,
                    )
                    return Failure(save_result.error)
                publish_result = await self.event_publisher.publish(event)
                if not publish_result.is_success:
                    self.logger.structured_log(
                        "ERROR",
                        f"Failed to publish event {event.event_type}",
                        event_id=event.event_id,
                        aggregate_id=event.aggregate_id,
                        error=publish_result.error,
                    )
                    return Failure(publish_result.error)
            self.logger.structured_log(
                "INFO",
                f"Aggregate {entity.id} persisted with {len(new_events)} new events.",
                aggregate_id=entity.id,
                event_count=len(new_events),
            )
            return Success(None)
        except Exception as exc:
            self.logger.structured_log(
                "ERROR",
                f"Exception persisting aggregate {entity.id}",
                aggregate_id=entity.id,
                exc_info=exc,
            )
            return Failure(exc)

    async def remove(self, id: str) -> Result[None, Exception]:
        """
        Remove an aggregate by ID (soft delete pattern: emit a Deleted event).
        Emits and persists a DeletedEvent if the aggregate exists.
        Returns:
            Success(None) if deleted, Failure(error) otherwise.
        """
        self.logger.structured_log(
            "INFO",
            f"Aggregate {id} removal requested (event sourcing: soft delete)",
            aggregate_id=id,
        )
        try:
            aggregate_result = await self.get_by_id(id)
            if not aggregate_result.is_success:
                self.logger.structured_log(
                    "ERROR",
                    f"Failed to load aggregate {id} for deletion",
                    aggregate_id=id,
                    error=aggregate_result.error,
                )
                return Failure(aggregate_result.error)
            aggregate = aggregate_result.value
            if aggregate is None:
                self.logger.structured_log(
                    "WARNING",
                    f"Aggregate {id} not found for deletion (no-op)",
                    aggregate_id=id,
                )
                return Success(None)
            deleted_event = DeletedEvent(aggregate_id=id)
            save_result = await self.event_store.save_event(deleted_event)
            if not save_result.is_success:
                self.logger.structured_log(
                    "ERROR",
                    f"Failed to save DeletedEvent for aggregate {id}",
                    aggregate_id=id,
                    error=save_result.error,
                )
                return Failure(save_result.error)
            publish_result = await self.event_publisher.publish(deleted_event)
            if not publish_result.is_success:
                self.logger.structured_log(
                    "ERROR",
                    f"Failed to publish DeletedEvent for aggregate {id}",
                    aggregate_id=id,
                    error=publish_result.error,
                )
                return Failure(publish_result.error)
            self.logger.structured_log(
                "INFO",
                f"Aggregate {id} marked as deleted (DeletedEvent emitted)",
                aggregate_id=id,
            )
            return Success(None)
        except Exception as exc:
            self.logger.structured_log(
                "ERROR",
                f"Exception during aggregate {id} soft delete",
                aggregate_id=id,
                exc_info=exc,
            )
            return Failure(exc)
