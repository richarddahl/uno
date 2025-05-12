"""
AggregateRoot base class for Uno's DDD/event sourcing model.
"""

from __future__ import annotations

from typing import TypeVar, TYPE_CHECKING

from pydantic import ConfigDict, PrivateAttr

if TYPE_CHECKING:
    from uno.domain.protocols import (
        AggregateRootProtocol,
        DomainEventProtocol,
        EventPublisherProtocol,
    )
    from uno.logging.protocols import LoggerProtocol

from uno.domain.entity import Entity
from uno.domain.errors import AggregateNotDeletedError, DomainValidationError
from uno.events.deleted_event import DeletedEvent
from uno.events.restored_event import RestoredEvent

T_ID = TypeVar("T_ID")


class AggregateRoot(Entity[T_ID]):
    """
    Base class for aggregate roots with event sourcing lifecycle and soft delete/restore support.

    Aggregates are intentionally mutable to support event sourcing and transactional workflows.
    All state changes must be made via domain events and explicit mutation methods.

    Example:
        class MyAggregate(AggregateRoot[int]):
            ...
        events = [SomeCreated(...), SomeUpdated(...)]
        result = MyAggregate.from_events(events)
        if isinstance(result, Success):
            agg = result.value
        else:
            # handle error
            ...
    """

    _logger: LoggerProtocol | None = None  # Inject via DI or set externally
    _events: list[DomainEventProtocol] = PrivateAttr(default_factory=list)
    version: int = 0
    _is_deleted: bool = PrivateAttr(default=False)

    @property
    def is_deleted(self) -> bool:
        """
        Returns True if the aggregate has been soft deleted (DeletedEvent applied and not restored).
        """
        return self._is_deleted

    def get_uncommitted_events(self) -> list[DomainEventProtocol]:
        """
        Returns a copy of the list of uncommitted domain events since last persistence.
        """
        return list(self._events)

    def enforce_invariants(self) -> None:
        """
        Override in subclasses to enforce aggregate invariants after event application.
        Raise an exception if invariants are violated.
        """
        pass

    def validate(self) -> None:
        """
        Validate the aggregate's invariants. Override in subclasses for custom validation.
        Raises:
            DomainValidationError: If validation fails.
        """
        try:
            # Custom validation logic here
            pass
        except Exception as exc:
            if self._logger:
                self._logger.error(
                    f"Invariant check failed for aggregate {self}: {exc}"
                )
            raise DomainValidationError(f"Validation failed: {exc}") from exc

    def add_event(self, event: DomainEventProtocol) -> None:
        """
        Adds an event to the aggregate and marks it as uncommitted.
        """
        if isinstance(event, RestoredEvent) and not self.is_deleted:
            self._logger.error(f"Cannot restore aggregate {self.id}: not deleted.")
            raise AggregateNotDeletedError(
                f"Cannot restore aggregate {self.id}: not deleted."
            )
        self.apply_event(event)
        self._events.append(event)
        self.version += 1
        self._logger.info(f"Event {event.event_type} added to aggregate {self.id}.")

    def clear_events(self) -> None:
        self._events.clear()

    def apply_event(self, event: DomainEventProtocol) -> None:
        handler_name = f"apply_{event.event_type}"
        if hasattr(self, handler_name):
            getattr(self, handler_name)(event)
        # Defensive: fallback if event_type string doesn't match
        elif isinstance(event, DeletedEvent):
            self.apply_deleted(event)
        elif isinstance(event, RestoredEvent):
            self.apply_restored(event)

    def apply_deleted(self, event: DeletedEvent) -> None:
        self._is_deleted = True

    def apply_restored(self, event: RestoredEvent) -> None:
        self._is_deleted = False

    @classmethod
    def from_events(cls, events: list[DomainEventProtocol]) -> AggregateRootProtocol:
        """
        Rehydrates an aggregate from a list of events.
        Returns:
            The rehydrated aggregate instance.
        Raises:
            Exception: If no events are provided or rehydration fails.
        """
        if not events:
            raise Exception(f"No events to rehydrate aggregate for {cls.__name__}.")
        try:
            instance = cls(id=getattr(events[0], "aggregate_id", None))
            for event in events:
                instance.apply_event(event)
                instance.version += 1
            return instance
        except Exception as exc:
            raise Exception(
                f"Error rehydrating aggregate {cls.__name__} from events: {exc}"
            ) from exc

    def assert_not_deleted(self) -> None:
        """
        Ensures the aggregate is not deleted.
        Raises:
            AggregateNotDeletedError: If the aggregate is deleted.
        """
        if self.is_deleted:
            self._logger.error(f"Aggregate {self.id} is deleted and cannot be mutated.")
            raise AggregateNotDeletedError(
                f"Aggregate {self.id} is deleted and cannot be mutated."
            )

    async def publish_events(self, publisher: EventPublisherProtocol) -> None:
        """
        Publishes all uncommitted events using the provided publisher.

        Args:
            publisher: The event publisher to use for publishing events.

        Raises:
            Exception: If publishing fails for any event.
        """
        for event in self.get_uncommitted_events():
            try:
                await publisher.publish(event)
                self._logger.info(
                    f"Published event {event.event_type} for aggregate {self.id}."
                )
            except Exception as exc:
                self._logger.error(f"Failed to publish event {event.event_type}: {exc}")
                raise

        # Clear events after successful publishing
        self.clear_events()

    model_config = ConfigDict(frozen=False, extra="forbid")
