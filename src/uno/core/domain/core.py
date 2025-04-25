# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
Core domain components for the Uno framework.

This module provides the foundational classes for implementing a domain-driven design
approach in the Uno framework, including entities, value objects, aggregates, and events.
"""

from __future__ import annotations

# Standard library imports
import uuid
from datetime import datetime
from typing import Any, Generic, TypeVar

# Third-party imports
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

# Import from base types to avoid circular imports
from uno.core.domain._base_types import BaseDomainEvent

# Define DomainEvent as an alias of BaseDomainEvent for backward compatibility
DomainEvent = BaseDomainEvent


class ValueObject(BaseModel):
    """
    Base class for value objects.

    Value objects are immutable objects that contain attributes but lack a conceptual identity.
    They are used to represent concepts within your domain that are defined by their attributes
    rather than by an identity.

    Examples include Money, Address, and DateRange.
    """

    model_config = ConfigDict(frozen=True)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.model_dump() == other.model_dump()

    def __hash__(self):
        return hash(tuple(sorted(self.model_dump().items())))


T_ID = TypeVar("T_ID")  # Entity ID type


class Entity(BaseModel, Generic[T_ID]):
    """
    Base class for domain entities.

    Entities are objects that have a distinct identity that runs through time and
    different states. They are defined by their identity, not by their attributes.
    """

    # Allow arbitrary types to support rich domain models
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: T_ID = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(datetime.UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(datetime.UTC))
    deleted_at: datetime | None = None

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    @model_validator(mode="before")
    def set_updated_at(self, values):
        """Update the updated_at field whenever the entity is modified."""
        # Only set updated_at for existing entities that are being modified
        if values is None:
            return values
        data = values.data if hasattr(values, "data") else values
        if data is None:
            return values
        if data.get("id") and data.get("created_at"):
            data["updated_at"] = datetime.now(datetime.UTC)
        return data

    # Python 3.13 compatibility methods for dataclasses



T = TypeVar("T", bound=Entity)
T_Child = TypeVar("T_Child", bound=Entity)


class AggregateRoot(Entity[T_ID]):
    """
    Base class for aggregate roots with event sourcing capabilities.

    Aggregate roots are the entry point to an aggregate - a cluster of domain objects
    that can be treated as a single unit. They encapsulate related domain objects and
    define boundaries for transactions and consistency.

    This class supports event sourcing: aggregates are mutated only by applying events,
    and can be rehydrated from an event stream.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    _events: list[Any] = PrivateAttr(default_factory=list)  # Typed as Any to avoid circular reference
    _child_entities: set[Entity] = PrivateAttr(default_factory=set)




    def add_event(self, event: Any) -> None:
        """
        Add a domain event to this aggregate and apply it to mutate state.
        """
        if not hasattr(self, "_events") or self._events is None:
            self._events = []
        self.apply_event(event)
        self._events.append(event)

    def clear_events(self) -> list[Any]:
        """
        Clear all domain events from this aggregate.
        Returns the list of events that were cleared.
        """
        if not hasattr(self, "_events") or self._events is None:
            self._events = []
            return []
        events = self._events.copy()
        self._events.clear()
        return events

    def register_child_entity(self, entity: Entity) -> None:
        if not hasattr(self, "_child_entities") or self._child_entities is None:
            self._child_entities = set()
        self._child_entities.add(entity)

    def get_child_entities(self) -> set[Entity]:
        if not hasattr(self, "_child_entities") or self._child_entities is None:
            self._child_entities = set()
        return self._child_entities

    @classmethod
    def from_events(cls: type[T], events: list[Any]) -> T:
        """
        Rehydrate an aggregate from a stream of events.
        """
        if not events:
            raise ValueError("Cannot rehydrate aggregate from empty event stream.")
        # Create a new instance with the ID and base fields from the first event
        base_data = {
            "id": events[0].aggregate_id,
            # Optionally: set created_at/updated_at from event timestamps
        }
        aggregate = cls(**base_data)  # type: ignore
        for event in events:
            aggregate.apply_event(event)
        return aggregate

    def apply_event(self, event: Any) -> None:
        """
        Apply a domain event to mutate the aggregate's state.
        Calls a method named 'apply_<event_type>' if present, else does nothing.
        """
        event_type = event.event_type.lower()
        if "." in event_type:
            event_type = event_type.split(".")[-1]
        handler_name = f"apply_{event_type}"
        handler = getattr(self, handler_name, None)
        if callable(handler):
            handler(event)
        # else: silently ignore if no handler is present
