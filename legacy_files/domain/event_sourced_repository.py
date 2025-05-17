"""
Event-sourced repository for Uno DDD aggregates.

This module provides a generic, DI-ready repository that persists and rehydrates aggregates
using the event sourcing pattern. Integrates with Uno's DI, logging, error, and config systems.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

from uno.domain.aggregate import AggregateRoot
from uno.domain.errors import DomainError

if TYPE_CHECKING:
    from uno.domain.protocols import (
        AggregateRootProtocol,
        DomainEventProtocol,
        RepositoryProtocol,
    )
    from uno.persistance.event_sourcing.protocols import EventStoreProtocol
    from uno.snapshots.protocols import SnapshotStoreProtocol, SnapshotStrategyProtocol

if TYPE_CHECKING:
    from uno.domain.config import DomainConfig
    from uno.events.publisher import EventPublisherProtocol
    from uno.logging.protocols import LoggerProtocol

# Type variables for generic type hints
T = TypeVar("T", bound=AggregateRootProtocol)
E = TypeVar("E", bound=DomainEventProtocol)


class EventSourcedRepository(Generic[T], RepositoryProtocol[T]):
    """
    Repository implementation that uses event sourcing for aggregate persistence.

    Loads aggregates by replaying events from the event store, and saves aggregates
    by persisting new events and publishing them via the event bus/publisher.
    """

    def __init__(
        self,
        aggregate_type: type[T],
        event_store: EventStoreProtocol[E],
        event_publisher: EventPublisherProtocol,
        logger: LoggerProtocol,
        config: DomainConfig,
        snapshot_store: SnapshotStoreProtocol | None = None,
        snapshot_strategy: SnapshotStrategyProtocol | None = None,
    ) -> None:
        """
        Initialize the repository.

        Args:
            aggregate_type: The aggregate root type
            event_store: The event store implementation
            event_publisher: The event publisher/bus
            logger: LoggerProtocol for structured logging
            config: Domain configuration settings
            snapshot_store: Optional store for aggregate snapshots
            snapshot_strategy: Optional strategy to determine when to take snapshots
        """
        self.aggregate_type = aggregate_type
        self.event_store = event_store
        self.event_publisher = event_publisher
        self.logger = logger
        self.config = config
        self.snapshot_store = snapshot_store
        self.snapshot_strategy = snapshot_strategy

    async def get_by_id(self, aggregate_id: str) -> T | None:
        """
        Load an aggregate by ID by replaying its event stream.

        If snapshots are enabled, tries to load from snapshot first to optimize loading.

        Args:
            aggregate_id: The ID of the aggregate to load

        Returns:
            The aggregate if found, or None if not found.

        Raises:
            UnoError: If an error occurs while loading events.
        """
        try:
            self.logger.info(
                "Loading aggregate",
                aggregate_id=aggregate_id,
                aggregate_type=self.aggregate_type.__name__,
            )

            # Try to load from snapshot if available
            aggregate = None
            latest_version = 0

            if self.snapshot_store:
                snapshot = await self.snapshot_store.get_latest_snapshot(aggregate_id)
                if snapshot:
                    latest_version = snapshot.aggregate_version
                    # Create aggregate from snapshot
                    aggregate = cast("T", self.aggregate_type())
                    # Apply the snapshot if the aggregate supports it
                    if hasattr(aggregate, "apply_snapshot"):
                        await aggregate.apply_snapshot(snapshot)  # type: ignore[attr-defined]

                    await self.logger.debug(
                        "Loaded aggregate from snapshot",
                        aggregate_id=aggregate_id,
                        aggregate_type=self.aggregate_type.__name__,
                        version=latest_version,
                    )

            # Load events after the snapshot version
            events = cast(
                "list[E]",
                await self.event_store.get_events(
                    aggregate_id=aggregate_id,
                    version=latest_version if latest_version > 0 else None,
                    max_events=self.config.max_events_per_aggregate,
                ),
            )

            if not events and aggregate is None:
                await self.logger.info(
                    "Aggregate not found",
                    aggregate_id=aggregate_id,
                    aggregate_type=self.aggregate_type.__name__,
                )
                return None

            # Check against max events limit from config
            if len(events) > self.config.max_events_per_aggregate:
                await self.logger.warning(
                    "Aggregate has exceeded maximum event count",
                    aggregate_id=aggregate_id,
                    aggregate_type=self.aggregate_type.__name__,
                    event_count=len(events),
                    max_events=self.config.max_events_per_aggregate,
                )

            # Create a new aggregate from events if no snapshot was used
            if aggregate is None:
                aggregate = cast("T", self.aggregate_type.from_events(events))
            else:
                # Otherwise apply the events after the snapshot
                for event in events:
                    if hasattr(aggregate, "apply"):
                        await aggregate.apply(event)  # type: ignore[attr-defined]

            await self.logger.debug(
                "Aggregate loaded successfully",
                aggregate_id=aggregate_id,
                aggregate_type=self.aggregate_type.__name__,
                from_snapshot=latest_version > 0,
                event_count=len(events),
            )

            return aggregate
        except Exception as exc:
            error_msg = f"Failed to load aggregate {aggregate_id}"
            self.logger.error(
                error_msg,
                aggregate_id=aggregate_id,
                aggregate_type=self.aggregate_type.__name__,
                error=str(exc),
                exc_info=exc,
            )
            if isinstance(exc, DomainError):
                raise
            raise DomainError(
                message=error_msg,
                code="REPOSITORY_LOAD_ERROR",
                aggregate_id=aggregate_id,
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
            await self.logger.info(
                "Listing all aggregates",
                aggregate_type=self.aggregate_type.__name__,
            )

            all_events = cast(
                "list[E]",
                await self.event_store.get_events_by_aggregate_id(
                    self.aggregate_type.__name__
                ),
            )

            aggregates: dict[str, list[E]] = {}
            for event in all_events:
                if hasattr(event, "aggregate_id"):
                    aggregates.setdefault(event.aggregate_id, []).append(event)

            result: list[T] = [
                cast("T", self.aggregate_type.from_events(evts))
                for evts in aggregates.values()
            ]

            await self.logger.info(
                "Aggregates loaded",
                aggregate_type=self.aggregate_type.__name__,
                count=len(result),
            )

            return result
        except Exception as exc:
            error_msg = (
                f"Failed to list aggregates of type {self.aggregate_type.__name__}"
            )
            await self.logger.error(
                error_msg,
                aggregate_type=self.aggregate_type.__name__,
                error=str(exc),
                exc_info=exc,
            )
            if isinstance(exc, DomainError):
                raise
            raise DomainError(
                message=error_msg,
                code="REPOSITORY_LIST_ERROR",
                aggregate_type=self.aggregate_type.__name__,
            ) from exc

    async def save(self, aggregate: T) -> None:
        """
        Persist new events from the aggregate and publish them.

        If snapshots are enabled, may take a snapshot based on the configured strategy.

        Args:
            aggregate: The aggregate to persist

        Raises:
            UnoError: If an error occurs while saving or publishing events.
        """
        try:
            new_events = aggregate.get_uncommitted_events()

            if not new_events:
                await self.logger.debug(
                    "No new events to persist",
                    aggregate_id=aggregate.id,
                    aggregate_type=self.aggregate_type.__name__,
                )
                return

            await self.logger.info(
                "Persisting aggregate events",
                aggregate_id=aggregate.id,
                aggregate_type=self.aggregate_type.__name__,
                event_count=len(new_events),
            )

            for event in new_events:
                # Assuming set_event_hash is available on the protocol or implementation
                if hasattr(event, "set_event_hash"):
                    event.set_event_hash()
                await self.event_store.save_event(event)
                await self.event_publisher.publish(event)

            # Clear events after they've been persisted
            if hasattr(aggregate, "clear_events"):
                aggregate.clear_events()

            # Handle snapshot if strategy and store are available
            if self.snapshot_store and self.snapshot_strategy:
                current_version = getattr(aggregate, "version", 0)
                if await self.snapshot_strategy.should_snapshot(
                    aggregate.id, current_version
                ):
                    # Get state for snapshot if the aggregate supports it
                    if hasattr(aggregate, "get_snapshot_state"):
                        state = await aggregate.get_snapshot_state()  # type: ignore[attr-defined]
                        await self.snapshot_store.save_snapshot(
                            aggregate_id=aggregate.id,
                            aggregate_version=current_version,
                            state=state,
                        )
                        await self.logger.debug(
                            "Created aggregate snapshot",
                            aggregate_id=aggregate.id,
                            aggregate_type=self.aggregate_type.__name__,
                            version=current_version,
                        )

            await self.logger.info(
                "Aggregate persisted successfully",
                aggregate_id=aggregate.id,
                aggregate_type=self.aggregate_type.__name__,
                event_count=len(new_events),
            )
        except Exception as exc:
            error_msg = f"Failed to persist aggregate {aggregate.id}"
            await self.logger.error(
                error_msg,
                aggregate_id=aggregate.id,
                aggregate_type=self.aggregate_type.__name__,
                error=str(exc),
                exc_info=exc,
            )
            if isinstance(exc, DomainError):
                raise
            raise DomainError(
                message=error_msg,
                code="REPOSITORY_SAVE_ERROR",
                aggregate_id=aggregate.id,
                aggregate_type=self.aggregate_type.__name__,
            ) from exc

    async def delete(self, aggregate_id: str) -> None:
        """
        Remove an aggregate by ID (soft delete pattern: emit a Deleted event).
        Emits and persists a DeletedEvent if the aggregate exists.

        Args:
            aggregate_id: The ID of the aggregate to remove

        Raises:
            UnoError: If an error occurs during the removal process.
        """
        await self.logger.info(
            "Removing aggregate (soft delete)",
            aggregate_id=aggregate_id,
            aggregate_type=self.aggregate_type.__name__,
        )

        try:
            aggregate = await self.get_by_id(aggregate_id)

            if aggregate is None:
                await self.logger.warning(
                    "Aggregate not found for deletion",
                    aggregate_id=aggregate_id,
                    aggregate_type=self.aggregate_type.__name__,
                )
                return

            deleted_event = DeletedEvent()
            if hasattr(deleted_event, "aggregate_id"):
                deleted_event.aggregate_id = aggregate_id  # type: ignore[attr-defined]

            # Ensure DeletedEvent is compatible with the event store's expected type
            deleted_event.aggregate_id = aggregate_id  # type: ignore[attr-defined]
            # Type ignore because we know DeletedEvent is compatible with E
            # and we're already awaiting the coroutines
            await self.event_store.save_event(deleted_event)  # type: ignore[arg-type, unused-awaitable]
            await self.event_publisher.publish(deleted_event)  # type: ignore[arg-type, unused-awaitable]

            await self.logger.info(
                "Aggregate marked as deleted",
                aggregate_id=aggregate_id,
                aggregate_type=self.aggregate_type.__name__,
            )
        except Exception as exc:
            error_msg = f"Failed to remove aggregate {aggregate_id}"
            self.logger.error(
                error_msg,
                aggregate_id=aggregate_id,
                aggregate_type=self.aggregate_type.__name__,
                error=str(exc),
                exc_info=exc,
            )
            if isinstance(exc, DomainError):
                raise
            raise DomainError(
                message=error_msg,
                code="REPOSITORY_REMOVE_ERROR",
                aggregate_id=aggregate_id,
                aggregate_type=self.aggregate_type.__name__,
            ) from exc
