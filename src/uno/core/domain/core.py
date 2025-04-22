# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
Core domain components for the Uno framework.

This module provides the foundational classes for implementing a domain-driven design
approach in the Uno framework, including entities, value objects, aggregates, and events.
"""

import uuid
from datetime import datetime, timezone
from typing import (
    Any,
    Generic,
    TypeVar,
    list,
    set,
)

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DomainEvent(BaseModel):
    """
    Base class for domain events.

    Domain events represent something significant that occurred within the domain.
    They are used to communicate between different parts of the application
    and to enable event-driven architectures.
    """

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = Field(default="domain_event")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DomainEvent":
        """Create an event from a dictionary."""
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert event to a dictionary."""
        return self.model_dump()


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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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
        if values.get("id") and values.get("created_at"):
            values["updated_at"] = datetime.now(timezone.utc)
        return values

    # Python 3.13 compatibility methods for dataclasses
    def __post_init__(self):
        """
        Handle initialization after dataclass processing.

        This method is called by dataclasses after the object is initialized.
        Override it in subclasses to handle additional initialization
        requirements, but be sure to call super().__post_init__() first.
        """
        # Ensure object attributes are properly initialized
        for field_name, field_value in self.__annotations__.items():
            # Check if this is a collection that might need initialization
            if hasattr(self, field_name):
                continue  # Field already exists

            # Handle dictionary fields
            if (
                field_value == dict
                or isinstance(field_value, type)
                and issubclass(field_value, dict)
            ):
                setattr(self, field_name, {})
            # Handle list fields
            elif (
                field_value == list
                or isinstance(field_value, type)
                and issubclass(field_value, list)
            ):
                setattr(self, field_name, [])
            # Handle set fields
            elif (
                field_value == Set
                or isinstance(field_value, type)
                and issubclass(field_value, Set)
            ):
                setattr(self, field_name, set())


T = TypeVar("T", bound=Entity)
T_Child = TypeVar("T_Child", bound=Entity)


class AggregateRoot(Entity[T_ID]):
    """
    Base class for aggregate roots.

    Aggregate roots are the entry point to an aggregate - a cluster of domain objects
    that can be treated as a single unit. They encapsulate related domain objects and
    define boundaries for transactions and consistency.

    Examples include Order (which contains OrderLines), User (which contains Addresses).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Add type annotations to mark class attributes
    # These can be used to hold instance attributes that should be properly initialized
    _events: list[DomainEvent]
    _child_entities: Set[Entity]

    def __init__(self, **data):
        super().__init__(**data)
        # Initialize instance-specific collections
        self._events = []
        self._child_entities = set()

    # Override __post_init__ from Entity to handle dataclass compatibility
    def __post_init__(self):
        """
        Handle initialization after dataclass processing for aggregate roots.

        This method ensures that all necessary collections are properly initialized,
        even when the object is created through dataclass processing.
        """
        super().__post_init__()

        # Explicitly initialize our instance collections
        if not hasattr(self, "_events") or self._events is None:
            self._events = []
        if not hasattr(self, "_child_entities") or self._child_entities is None:
            self._child_entities = set()

    def add_event(self, event: DomainEvent) -> None:
        """
        Add a domain event to this aggregate.

        Domain events are collected within the aggregate and can be processed
        after the aggregate is saved.

        Args:
            event: The domain event to add
        """
        if not hasattr(self, "_events") or self._events is None:
            self._events = []
        self._events.append(event)

    def clear_events(self) -> list[DomainEvent]:
        """
        Clear all domain events from this aggregate.

        Returns:
            The list of events that were cleared
        """
        if not hasattr(self, "_events") or self._events is None:
            self._events = []
            return []

        events = self._events.copy()
        self._events.clear()
        return events

    def register_child_entity(self, entity: Entity) -> None:
        """
        Register a child entity with this aggregate root.

        Args:
            entity: The child entity to register
        """
        if not hasattr(self, "_child_entities") or self._child_entities is None:
            self._child_entities = set()
        self._child_entities.add(entity)

    def get_child_entities(self) -> Set[Entity]:
        """
        Get all child entities of this aggregate root.

        Returns:
            The set of child entities
        """
        if not hasattr(self, "_child_entities") or self._child_entities is None:
            self._child_entities = set()
        return self._child_entities
