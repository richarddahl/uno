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

from collections.abc import Callable
from typing import Any, Generic, TypeVar

from uno.core.domain.core import T_ID, AggregateRoot, DomainEvent
from uno.core.domain.repository import Repository

T = TypeVar("T", bound=AggregateRoot)


class DomainEventDispatcher:
    """Dispatches domain events to registered handlers."""

    _handlers: dict[type[DomainEvent], list[Callable]] = {}

    @classmethod
    def register(cls, event_type: type[DomainEvent], handler: Callable) -> None:
        """Register a handler for a specific event type."""
        if event_type not in cls._handlers:
            cls._handlers[event_type] = []
        cls._handlers[event_type].append(handler)

    @classmethod
    async def dispatch(cls, event: DomainEvent) -> None:
        """Dispatch an event to all registered handlers."""
        event_type = type(event)
        if event_type in cls._handlers:
            for handler in cls._handlers[event_type]:
                await handler(event)


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
        await self._dispatch_domain_events(aggregate)
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
        await self._dispatch_domain_events(aggregate)
        return result

    async def delete(self, id: T_ID) -> bool:
        """Delete an aggregate by ID."""
        aggregate = await self.repository.get_by_id(id)
        if not aggregate:
            return False

        await self.repository.delete(aggregate)
        await self._dispatch_domain_events(aggregate)
        return True

    async def _dispatch_domain_events(self, aggregate: AggregateRoot) -> None:
        """Dispatch domain events from an aggregate."""
        if hasattr(aggregate, "_events"):
            events = aggregate._events
            aggregate._events = []

            for event in events:
                await DomainEventDispatcher.dispatch(event)
