"""
AggregateRoot base class for Uno's DDD/event sourcing model.
"""
from __future__ import annotations
from typing import TypeVar
from pydantic import PrivateAttr, ConfigDict
from uno.core.domain.entity import Entity
from uno.core.events.base_event import DomainEvent
from uno.core.events.deleted_event import DeletedEvent
from uno.core.events.restored_event import RestoredEvent
from uno.core.errors import Success, Failure, AggregateNotDeletedError


T_ID = TypeVar("T_ID")

class AggregateRoot(Entity[T_ID]):
    """
    Base class for aggregate roots with event sourcing lifecycle and soft delete/restore support.
    """
    _events: list[DomainEvent] = PrivateAttr(default_factory=list)
    version: int = 0
    _is_deleted: bool = PrivateAttr(default=False)

    @property
    def is_deleted(self) -> bool:
        """
        Returns True if the aggregate has been soft deleted (DeletedEvent applied and not restored).
        """
        return self._is_deleted

    def add_event(self, event: DomainEvent) -> Success[None, Exception] | Failure[None, Exception]:
        """
        Adds an event to the aggregate. Prevents restoring if not deleted.
        Returns:
            Success[None, Exception](None) if added, Failure[None, Exception](AggregateNotDeletedError) if restoring when not deleted.
        """
        if isinstance(event, RestoredEvent) and not self.is_deleted:
            return Failure[None, Exception](AggregateNotDeletedError(f"Cannot restore aggregate {self.id}: not deleted."))
        self.apply_event(event)
        self._events.append(event)
        self.version += 1
        return Success[None, Exception](None)

    def clear_events(self) -> None:
        self._events.clear()

    def apply_event(self, event: DomainEvent) -> None:
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
    def from_events(cls, events: list[DomainEvent]) -> AggregateRoot:
        if not events:
            raise ValueError("No events to rehydrate aggregate.")
        instance = cls(id=getattr(events[0], "aggregate_id", None))
        for event in events:
            instance.apply_event(event)
            instance.version += 1
        return instance

    def assert_not_deleted(self) -> Success[None, Exception] | Failure[None, Exception]:
        if self.is_deleted:
            return Failure[None, Exception](AggregateNotDeletedError(f"Aggregate {self.id} is deleted and cannot be mutated."))
        return Success[None, Exception](None)

    model_config = ConfigDict(frozen=False, extra="forbid")
