"""
AggregateRoot base class for Uno's DDD/event sourcing model.
"""
from __future__ import annotations
from typing import Any, Generic, TypeVar
from pydantic import Field
from uno.core.domain.entity import Entity
from uno.core.events.base_event import DomainEvent

T_ID = TypeVar("T_ID")

class AggregateRoot(Entity[T_ID]):
    """
    Base class for aggregate roots with event sourcing lifecycle.
    """
    _events: list[DomainEvent] = Field(default_factory=list, exclude=True)
    version: int = 0

    def add_event(self, event: DomainEvent) -> None:
        self.apply_event(event)
        self._events.append(event)
        self.version += 1

    def clear_events(self) -> None:
        self._events.clear()

    def apply_event(self, event: DomainEvent) -> None:
        handler_name = f"apply_{event.event_type}"
        if hasattr(self, handler_name):
            getattr(self, handler_name)(event)

    @classmethod
    def from_events(cls, events: list[DomainEvent]) -> AggregateRoot:
        if not events:
            raise ValueError("No events to rehydrate aggregate.")
        instance = cls(id=getattr(events[0], "aggregate_id", None))
        for event in events:
            instance.apply_event(event)
            instance.version += 1
        return instance

    class Config:
        frozen = False
        extra = "forbid"
