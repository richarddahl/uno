"""Repository pattern implementation for domain objects.

This module provides the base implementation and protocols for repositories
that manage domain entities.
"""

from __future__ import annotations
from typing import TypeVar, Generic, cast
from uuid import UUID
from uno.logging import LoggerProtocol, get_logger

T = TypeVar("T")
ID = TypeVar("ID", bound=UUID | str | int)


class BaseRepository(Generic[T, ID]):
    """Base implementation of the repository pattern.

    This class provides common functionality for all repository implementations.
    Concrete repositories should inherit from this class and implement the
    required methods.
    """

    def __init__(self, logger: LoggerProtocol | None = None) -> None:
        """Initialize the base repository.

        Args:
            logger: Optional logger instance. If not provided, a default one will be created.
        """
        self._logger = logger or get_logger(
            f"uno.repository.{self.__class__.__name__.lower()}"
        )

    async def get(self, id: ID) -> T | None:
        """Retrieve an entity by its ID.

        Must be implemented by subclasses.

        Args:
            id: The identifier of the entity to retrieve

        Returns:
            The entity if found, None otherwise

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement get()")

    async def add(self, entity: T) -> None:
        """Add a new entity to the repository.

        Must be implemented by subclasses.

        Args:
            entity: The entity to add

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement add()")

    async def update(self, entity: T) -> None:
        """Update an existing entity.

        Must be implemented by subclasses.

        Args:
            entity: The entity to update

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement update()")

    async def remove(self, entity: T) -> None:
        """Remove an entity from the repository.

        Must be implemented by subclasses.

        Args:
            entity: The entity to remove

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement remove()")

    def _get_entity_id(self, entity: T) -> ID:
        """Get the ID of an entity.

        This is a helper method that can be overridden by subclasses
        to customize how entity IDs are extracted.

        Args:
            entity: The entity to get the ID from

        Returns:
            The ID of the entity

        Raises:
            ValueError: If the entity doesn't have an ID
        """
        if hasattr(entity, "id"):
            # Use cast to tell the type checker this is the correct type
            return cast(ID, entity.id)
        raise ValueError(f"Entity {entity} does not have an 'id' attribute")
