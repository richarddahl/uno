"""Event store interface for persisting and retrieving aggregates and events."""

from __future__ import annotations

import abc
import uuid
from typing import Generic, List, Optional, Sequence, Type, TypeVar, Union

from pydantic import BaseModel

from uno.domain.aggregate import AggregateRoot
from uno.domain.events import DomainEvent

T = TypeVar("T", bound=AggregateRoot)


class EventStore(abc.ABC, Generic[T]):
    """Abstract base class for event stores.
    
    Provides methods for saving and loading aggregates, and querying events.
    """
    
    @abc.abstractmethod
    async def save(
        self,
        aggregate: T,
        expected_version: Optional[int] = None,
        **kwargs: Any
    ) -> None:
        """Save an aggregate's pending events to the event store.
        
        Args:
            aggregate: The aggregate root to save
            expected_version: The expected version of the aggregate for optimistic concurrency
            **kwargs: Additional implementation-specific arguments
            
        Raises:
            ConcurrencyError: If the aggregate version doesn't match expected_version
            EventStoreError: For other persistence errors
        """
        raise NotImplementedError
    
    @abc.abstractmethod
    async def load(
        self,
        aggregate_id: uuid.UUID,
        aggregate_type: Type[T],
        **kwargs: Any
    ) -> T:
        """Load an aggregate from the event store.
        
        Args:
            aggregate_id: The ID of the aggregate to load
            aggregate_type: The class of the aggregate to load
            **kwargs: Additional implementation-specific arguments
            
        Returns:
            The loaded aggregate
            
        Raises:
            AggregateNotFoundError: If the aggregate is not found
            EventStoreError: For other loading errors
        """
        raise NotImplementedError
    
    @abc.abstractmethod
    async def get_events(
        self,
        aggregate_id: uuid.UUID,
        **kwargs: Any
    ) -> Sequence[DomainEvent]:
        """Get all events for a specific aggregate.
        
        Args:
            aggregate_id: The ID of the aggregate
            **kwargs: Additional implementation-specific arguments
            
        Returns:
            A sequence of domain events for the aggregate
        """
        raise NotImplementedError
    
    @abc.abstractmethod
    async def get_aggregate_version(
        self,
        aggregate_id: uuid.UUID,
        **kwargs: Any
    ) -> Optional[int]:
        """Get the current version of an aggregate.
        
        Args:
            aggregate_id: The ID of the aggregate
            **kwargs: Additional implementation-specific arguments
            
        Returns:
            The current version of the aggregate, or None if not found
        """
        raise NotImplementedError


class EventStoreError(Exception):
    """Base exception for event store related errors."""
    pass


class AggregateNotFoundError(EventStoreError):
    """Raised when an aggregate is not found in the event store."""
    
    def __init__(self, aggregate_id: uuid.UUID) -> None:
        self.aggregate_id = aggregate_id
        super().__init__(f"Aggregate with ID {aggregate_id} not found")


class ConcurrencyError(EventStoreError):
    """Raised when there is a concurrency conflict."""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,
        expected_version: int,
        actual_version: int
    ) -> None:
        self.aggregate_id = aggregate_id
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(
            f"Concurrency conflict for aggregate {aggregate_id}. "
            f"Expected version {expected_version}, got {actual_version}"
        )
