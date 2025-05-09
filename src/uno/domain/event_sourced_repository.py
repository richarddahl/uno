"""
Event-sourced repository for Uno DDD aggregates.

This module provides a generic, DI-ready repository that persists and rehydrates aggregates
using the event sourcing pattern. Integrates with Uno's DI, logging, error, and config systems.
"""

from typing import Generic, TypeVar

from uno.domain.aggregate import AggregateRoot
from uno.domain.config import DomainConfig
from uno.domain.repository import Repository
from uno.errors.base import UnoError
from uno.events.deleted_event import DeletedEvent
from uno.events.event_store import EventStoreProtocol
from uno.events.publisher import EventPublisherProtocol
from uno.logging.protocols import LoggerProtocol

T = TypeVar("T", bound=AggregateRoot)


class EventSourcedRepository(Generic[T], Repository[T]):
    """
    Repository implementation that uses event sourcing for aggregate persistence.

    Loads aggregates by replaying events from the event store, and saves aggregates
    by persisting new events and publishing them via the event bus/publisher.
    """

    def __init__(
        self,
        aggregate_type: type[T],
        event_store: EventStoreProtocol,
        event_publisher: EventPublisherProtocol,
        logger: LoggerProtocol,
        config: DomainConfig,
    ):
        """
        Initialize the repository.

        Args:
            aggregate_type: The aggregate root type
            event_store: The event store implementation
            event_publisher: The event publisher/bus
            logger: LoggerProtocol for structured logging
            config: Domain configuration settings
        """
        self.aggregate_type = aggregate_type
        self.event_store = event_store
        self.event_publisher = event_publisher
        self.logger = logger
        self.config = config

    async def get_by_id(self, id: str) -> T | None:
        """
        Load an aggregate by ID by replaying its event stream.

        Args:
            id: The ID of the aggregate to load

        Returns:
            The aggregate if found, or None if not found.

        Raises:
            UnoError: If an error occurs while loading events.
        """
        try:
            self.logger.info(
                "Loading aggregate",
                aggregate_id=id,
                aggregate_type=self.aggregate_type.__name__,
            )

            events = await self.event_store.get_events_by_aggregate_id(id)

            if not events:
                self.logger.info(
                    "Aggregate not found",
                    aggregate_id=id,
                    aggregate_type=self.aggregate_type.__name__,
                )
                return None

            # Check against max events limit from config
            if len(events) > self.config.max_events_per_aggregate:
                self.logger.warning(
                    "Aggregate has exceeded maximum event count",
                    aggregate_id=id,
                    aggregate_type=self.aggregate_type.__name__,
                    event_count=len(events),
                    max_events=self.config.max_events_per_aggregate,
                )

            aggregate = self.aggregate_type.from_events(events)

            self.logger.debug(
                "Aggregate loaded successfully",
                aggregate_id=id,
                aggregate_type=self.aggregate_type.__name__,
                event_count=len(events),
            )

            return aggregate
        except Exception as exc:
            self.logger.error(
                "Failed to load aggregate",
                aggregate_id=id,
                aggregate_type=self.aggregate_type.__name__,
                error=str(exc),
                exc_info=exc,
            )
            if isinstance(exc, UnoError):
                raise
            raise UnoError(
                message=f"Failed to load aggregate {id}: {exc}",
                error_code="DOMAIN_REPOSITORY_LOAD_ERROR",
                category="DOMAIN",
                aggregate_id=id,
                aggregate_type=self.aggregate_type.__name__,
            ) from exc

    async def list(self) -> list[T]:
        """
        List all aggregates of this type (inefficient; for demo/testing only).

        Returns:
            A list of aggregates.

        Raises:
            UnoError: If an error occurs while loading events.
        """
        try:
            self.logger.info(
                "Listing all aggregates", aggregate_type=self.aggregate_type.__name__
            )

            all_events = await self.event_store.get_events_by_type(
                self.aggregate_type.__name__
            )

            aggregates: dict[str, list] = {}
            for event in all_events:
                aggregates.setdefault(event.aggregate_id, []).append(event)

            result = [
                self.aggregate_type.from_events(evts) for evts in aggregates.values()
            ]

            self.logger.info(
                "Aggregates loaded",
                aggregate_type=self.aggregate_type.__name__,
                count=len(result),
            )

            return result
        except Exception as exc:
            self.logger.error(
                "Failed to list aggregates",
                aggregate_type=self.aggregate_type.__name__,
                error=str(exc),
                exc_info=exc,
            )
            if isinstance(exc, UnoError):
                raise
            raise UnoError(
                message=f"Failed to list aggregates of type {self.aggregate_type.__name__}: {exc}",
                error_code="DOMAIN_REPOSITORY_LIST_ERROR",
                category="DOMAIN",
                aggregate_type=self.aggregate_type.__name__,
            ) from exc

    async def add(self, entity: T) -> None:
        """
        Persist new events from the aggregate and publish them.

        Args:
            entity: The aggregate to persist

        Raises:
            UnoError: If an error occurs while saving or publishing events.
        """
        try:
            new_events = entity.clear_events()

            if not new_events:
                self.logger.debug(
                    "No new events to persist",
                    aggregate_id=entity.id,
                    aggregate_type=self.aggregate_type.__name__,
                )
                return

            self.logger.info(
                "Persisting aggregate events",
                aggregate_id=entity.id,
                aggregate_type=self.aggregate_type.__name__,
                event_count=len(new_events),
            )

            for event in new_events:
                event.set_event_hash()
                await self.event_store.save_event(event)
                await self.event_publisher.publish(event)

            self.logger.info(
                "Aggregate persisted successfully",
                aggregate_id=entity.id,
                aggregate_type=self.aggregate_type.__name__,
                event_count=len(new_events),
            )
        except Exception as exc:
            self.logger.error(
                "Failed to persist aggregate",
                aggregate_id=entity.id,
                aggregate_type=self.aggregate_type.__name__,
                error=str(exc),
                exc_info=exc,
            )
            if isinstance(exc, UnoError):
                raise
            raise UnoError(
                message=f"Failed to persist aggregate {entity.id}: {exc}",
                error_code="DOMAIN_REPOSITORY_SAVE_ERROR",
                category="DOMAIN",
                aggregate_id=entity.id,
                aggregate_type=self.aggregate_type.__name__,
            ) from exc

    async def remove(self, id: str) -> None:
        """
        Remove an aggregate by ID (soft delete pattern: emit a Deleted event).
        Emits and persists a DeletedEvent if the aggregate exists.

        Args:
            id: The ID of the aggregate to remove

        Raises:
            UnoError: If an error occurs during the removal process.
        """
        self.logger.info(
            "Removing aggregate (soft delete)",
            aggregate_id=id,
            aggregate_type=self.aggregate_type.__name__,
        )

        try:
            aggregate = await self.get_by_id(id)

            if aggregate is None:
                self.logger.warning(
                    "Aggregate not found for deletion",
                    aggregate_id=id,
                    aggregate_type=self.aggregate_type.__name__,
                )
                return

            deleted_event = DeletedEvent(aggregate_id=id)
            await self.event_store.save_event(deleted_event)
            await self.event_publisher.publish(deleted_event)

            self.logger.info(
                "Aggregate marked as deleted",
                aggregate_id=id,
                aggregate_type=self.aggregate_type.__name__,
            )
        except Exception as exc:
            self.logger.error(
                "Failed to remove aggregate",
                aggregate_id=id,
                aggregate_type=self.aggregate_type.__name__,
                error=str(exc),
                exc_info=exc,
            )
            if isinstance(exc, UnoError):
                raise
            raise UnoError(
                message=f"Failed to remove aggregate {id}: {exc}",
                error_code="DOMAIN_REPOSITORY_REMOVE_ERROR",
                category="DOMAIN",
                aggregate_id=id,
                aggregate_type=self.aggregate_type.__name__,
            ) from exc
