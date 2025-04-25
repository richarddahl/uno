# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
Application services for the Uno framework.

This module provides base application service classes that orchestrate
domain objects and infrastructure services.
"""

# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT

from typing import Any, Generic, TypeVar

from uno.core.domain.core import T_ID, AggregateRoot
from uno.core.domain.repository import Repository

T = TypeVar("T", bound=AggregateRoot)


class ApplicationService(Generic[T, T_ID]):
    """Base class for application services."""

    # def __init__(self, repository: Repository[T, T_ID]):
    def __init__(self, repository: Repository[T]):
        """Initialize the service with a repository."""
        self.repository = repository

    async def get_by_id(self, id: T_ID) -> T | None:
        """Get an aggregate by ID."""
        return await self.repository.get_by_id(id)

    async def list(self, **filters) -> list[T]:
        """List aggregates with optional filtering."""
        return await self.repository.list(**filters)

    async def create(self, data: dict[str, Any], aggregate_class: type[T]) -> T:
        """Create a new aggregate."""
        aggregate = aggregate_class(**data)
        result = await self.repository.save(aggregate)
        return result

    async def update(self, id: T_ID, data: dict[str, Any]) -> T | None:
        """Update an existing aggregate."""
        aggregate = await self.repository.get_by_id(id)
        if not aggregate:
            return None

        # Update attributes
        for key, value in data.items():
            if hasattr(aggregate, key):
                setattr(aggregate, key, value)

        result = await self.repository.save(aggregate)
        return result

    async def delete(self, id: T_ID) -> bool:
        """Delete an aggregate by ID."""
        aggregate = await self.repository.get_by_id(id)
        if not aggregate:
            return False

        await self.repository.delete(aggregate)
        return True
