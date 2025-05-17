# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
domain.protocols
Domain protocols for Uno framework
"""

from typing import Protocol, TypeVar, Any, Generic
from datetime import datetime

T = TypeVar("T")
ID = TypeVar("ID")


class EntityProtocol(Protocol):
    """Base protocol for domain entities."""

    id: str
    created_at: datetime
    updated_at: datetime

    def update_timestamp(self) -> None: ...


class ValueObjectProtocol(Protocol):
    """Base protocol for value objects."""

    def __eq__(self, other: Any) -> bool: ...
    def __hash__(self) -> int: ...


class AggregateRootProtocol(Protocol[T]):
    """Base protocol for aggregate roots."""

    id: str
    version: int
    events: list[T]


class DomainEventProtocol(Protocol):
    """Base protocol for domain events."""

    event_id: str
    event_type: str
    occurred_on: datetime
    version: int


class AggregateEventProtocol(DomainEventProtocol, Protocol):
    """Protocol for domain events that are associated with an aggregate."""

    aggregate_id: str
    aggregate_version: int



class RepositoryProtocol(Protocol, Generic[T, ID]):
    """Protocol defining the standard interface for a domain repository.

    A repository is responsible for managing the persistence of domain entities.
    It provides methods to save, retrieve, and remove entities.
    """

    async def get(self, id: ID) -> T | None:
        """Retrieve an entity by its ID.

        Args:
            id: The identifier of the entity to retrieve

        Returns:
            The entity if found, None otherwise
        """
        ...

    async def add(self, entity: T) -> None:
        """Add a new entity to the repository.

        Args:
            entity: The entity to add
        """
        ...

    async def update(self, entity: T) -> None:
        """Update an existing entity.

        Args:
            entity: The entity to update
        """
        ...

    async def remove(self, entity: T) -> None:
        """Remove an entity from the repository.

        Args:
            entity: The entity to remove
        """
        ...
