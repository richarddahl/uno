"""
Protocol definitions for domain components.

This module provides protocols that define the interfaces for domain components
like entities, aggregates, value objects, and domain events.
"""

from __future__ import annotations

from typing import Any, ClassVar, Protocol, TypeVar, Generic, runtime_checkable


@runtime_checkable
class DomainEventProtocol(Protocol):
    """Protocol for domain events in event sourcing systems."""

    event_id: str
    aggregate_id: str
    event_type: ClassVar[str]
    version: int
    
    # Support for Pydantic model_dump()
    def model_dump(self, *, exclude_none: bool = False, exclude_unset: bool = False, by_alias: bool = False) -> dict[str, Any]:
        ...


class ValueObjectProtocol(Protocol):
    """Protocol for value objects in domain-driven design."""

    def __eq__(self, other: object) -> bool:
        """
        Compare this value object with another for equality.

        Args:
            other: The object to compare with

        Returns:
            True if the objects are equal, False otherwise
        """
        ...


class EntityProtocol(Protocol):
    """Protocol for entities in domain-driven design."""

    id: str

    def __eq__(self, other: object) -> bool:
        """
        Compare this entity with another for identity equality.

        Args:
            other: The object to compare with

        Returns:
            True if the objects have the same identity, False otherwise
        """
        ...


class AggregateRootProtocol(EntityProtocol, Protocol):
    """Protocol for aggregate roots in domain-driven design."""

    version: int

    async def apply(self, event: DomainEventProtocol) -> None:
        """
        Apply a domain event to this aggregate.

        Args:
            event: The domain event to apply
        """
        ...

    async def apply_event(self, event: Any) -> None:
        """
        Apply an event to this aggregate.

        Args:
            event: The event to apply
        """
        ...

    async def get_uncommitted_events(self) -> list[DomainEventProtocol]:
        """
        Get all uncommitted events.

        Returns:
            List of uncommitted events
        """
        ...

    async def clear_uncommitted_events(self) -> None:
        """Clear all uncommitted events."""
        ...


# Define the TypeVar for repository generic parameter - ensure it's properly exported
T = TypeVar("T", bound="AggregateRootProtocol")


class RepositoryProtocol(Protocol, Generic[T]):
    """Repository protocol for aggregate persistence."""

    async def get_by_id(self, aggregate_id: str) -> T | None:
        """
        Retrieve an aggregate by its ID.

        Args:
            aggregate_id: The ID of the aggregate to retrieve

        Returns:
            The aggregate if found, None otherwise
        """
        ...

    async def save(self, aggregate: T) -> None:
        """
        Save an aggregate.

        Args:
            aggregate: The aggregate to save
        """
        ...

    async def delete(self, aggregate_id: str) -> None:
        """
        Delete an aggregate by its ID.

        Args:
            aggregate_id: The ID of the aggregate to delete
        """
        ...
