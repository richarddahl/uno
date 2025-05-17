"""
Aggregate root base class for domain-driven design with event sourcing support.

This class provides a foundation for building domain aggregates with event sourcing
capabilities. It structurally implements the AggregateRootProtocol interface.
"""

from __future__ import annotations

import copy
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, cast, final, ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, PrivateAttr, model_validator, field_validator

from uno.domain.events import DomainEvent

# Type variables for aggregate and snapshot
S = TypeVar('S', bound='AggregateSnapshot')

E = TypeVar('E', bound=DomainEvent)
A = TypeVar('A', bound='AggregateRoot')

class AggregateRoot(Generic[E]):
    """Base class for all aggregate roots in the domain.
    
    An aggregate root is an entity that is the root of an aggregate and is responsible
    for maintaining the consistency of changes to the aggregate. It acts as the entry
    point for all modifications to the aggregate.
    
    The AggregateRoot class provides:
    - Event sourcing support
    - Versioning with optimistic concurrency control
    - Change tracking
    - Event application and raising
    - Snapshot support
    - Thread-safety for event application
    
    Subclasses should implement event handlers as methods named 'on_{event_type}'
    where event_type is the class name of the event.
    
    Example:
        class User(AggregateRoot):
            def __init__(self, username: str, email: str, **kwargs):
                super().__init__(**kwargs)
                self.username = username
                self.email = email
                
            def register(self, username: str, email: str):
                self._raise_event(UserRegistered(
                    username=username,
                    email=email
                ))
                
            def on_UserRegistered(self, event: UserRegistered) -> None:
                self.username = event.username
                self.email = event.email
    """
    
    _id: UUID = Field(default_factory=uuid4)
    _version: int = Field(default=0, ge=0)
    _pending_events: List[E] = Field(default_factory=list, exclude=True)
    _is_replaying: bool = Field(default=False, exclude=True)
    _created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    _updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    _lock: threading.RLock = PrivateAttr()
    _initial_version: int = 0
    
    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self._lock = threading.RLock()
        self._initial_version = int(self._version)
    
    @property
    def id(self) -> UUID:
        """Return the aggregate's unique identifier."""
        return self._id
    
    @property
    def version(self) -> int:
        """Return the aggregate's current version."""
        return self._version
    
    @property
    def pending_events(self) -> List[E]:
        """Return a copy of pending domain events."""
        return self._pending_events.copy()
    
    @property
    def created_at(self) -> datetime:
        """Return when the aggregate was created."""
        return self._created_at
    
    @property
    def updated_at(self) -> datetime:
        """Return when the aggregate was last updated."""
        return self._updated_at
        
    @classmethod
    @abstractmethod
    def create_snapshot(cls, aggregate: 'AggregateRoot[E]') -> 'AggregateSnapshot':
        """Create a snapshot of the aggregate's state.
        
        Subclasses should implement this to return a serializable snapshot.
        """
        raise NotImplementedError("Subclasses must implement create_snapshot")
        
    @classmethod
    @abstractmethod
    def restore_from_snapshot(cls, snapshot: 'AggregateSnapshot') -> 'AggregateRoot[E]':
        """Restore an aggregate from a snapshot.
        
        Subclasses should implement this to restore their state from a snapshot.
        """
        raise NotImplementedError("Subclasses must implement restore_from_snapshot")
    
    def clear_events(self) -> None:
        """Clear all pending domain events."""
        self._pending_events.clear()
    
    def _apply_event(self, event: E) -> None:
        """Apply a domain event to the aggregate.
        
        This method is thread-safe and ensures that events are applied atomically.
        
        Args:
            event: The domain event to apply
            
        Raises:
            ValueError: If the event causes an invariant violation
        """
        with self._lock:
            self._apply_event_unsafe(event)
    
    def _apply_event_unsafe(self, event: E) -> None:
        """Apply an event to the aggregate without acquiring a lock.
        
        This method is not thread-safe and should only be called from within a 
        thread-safe context or when thread-safety is not required.
        
        Args:
            event: The domain event to apply
            
        Raises:
            ValueError: If the event causes an invariant violation
        """
        # Find the event handler method (e.g., on_UserRegistered)
        handler_name = f"on_{event.__class__.__name__}"
        if hasattr(self, handler_name):
            handler = getattr(self, handler_name)
            if callable(handler):
                try:
                    handler(event)
                except Exception as e:
                    raise ValueError(
                        f"Error applying event {event.__class__.__name__} to {self.__class__.__name__}: {str(e)}"
                    ) from e
    
    def _raise_event(self, event: E) -> None:
        """Raise a new domain event and apply it to the aggregate.

        This method is thread-safe and ensures that events are applied atomically.
        It also handles versioning and updates the aggregate's state.

        Args:
            event: The domain event to raise and apply

        Raises:
            ValueError: If the event is invalid or causes an invariant violation
        """
        # Verify the event has required attributes
        if not hasattr(event, 'aggregate_id') or not hasattr(event, 'aggregate_version'):
            raise ValueError(
                f"Event {type(event).__name__} must have 'aggregate_id' and 'aggregate_version' fields. "
                f"It should implement DomainEvent protocol."
            )

        with self._lock:
            # Set the aggregate properties on the event
            event.aggregate_id = self.id
            
            # Calculate the next version
            next_version = self._version + 1
            event.aggregate_version = next_version

            try:
                # Apply the event to update the aggregate's state
                self._apply_event_unsafe(event)
                
                # Add the event to pending events
                self._pending_events.append(event)
                
                # Update the aggregate version and timestamp
                self._version = next_version
                self._updated_at = datetime.now(timezone.utc)
                
            except Exception as e:
                # If anything fails, ensure we don't leave the aggregate in an inconsistent state
                raise ValueError(
                    f"Failed to apply event {type(event).__name__} to {self.__class__.__name__}: {str(e)}"
                ) from e
    
    @classmethod
    def create(cls: type[A], **kwargs: Any) -> A:
        """Factory method to create a new aggregate instance.
        
        Args:
            **kwargs: Initial values for the aggregate
            
        Returns:
            A new instance of the aggregate
        """
        return cls(**kwargs)
    
    @classmethod
    def from_events(cls: type[A], events: List[E], **kwargs: Any) -> A:
        """Reconstruct an aggregate from a sequence of domain events.
        
        This method creates a new aggregate instance and applies all events in order.
        It's typically used when loading an aggregate from an event store.
        
        Args:
            events: The domain events to apply, in the order they occurred
            **kwargs: Additional arguments to pass to the aggregate's __init__ method
            
        Returns:
            A reconstructed instance of the aggregate with all events applied
            
        Raises:
            ValueError: If any event causes an invariant violation
        """
        if not events:
            return cls(**kwargs)
            
        # Create a new instance with replay flag set
        aggregate = cls(_is_replaying=True, **kwargs)
        
        try:
            # Apply each event in sequence
            for event in events:
                if not hasattr(event, 'aggregate_id') or not hasattr(event, 'aggregate_version'):
                    raise ValueError(
                        f"Event {type(event).__name__} is missing required aggregate fields. "
                        f"It should implement DomainEvent protocol."
                    )
                
                # Apply the event directly without version checks
                aggregate._apply_event_unsafe(event)
                
                # Update the version from the last event
                aggregate._version = event.aggregate_version
            
            # Set the initial version for optimistic concurrency
            aggregate._initial_version = aggregate._version
            
            # Clear the replay flag
            aggregate._is_replaying = False
            
            return aggregate
            
        except Exception as e:
            raise ValueError(
                f"Failed to reconstruct {cls.__name__} from events: {str(e)}"
            ) from e
    
    def __eq__(self, other: object) -> bool:
        """Compare aggregates by ID."""
        if not isinstance(other, AggregateRoot):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """Hash the aggregate by ID."""
        return hash(self.id)
    
    def mark_as_persisted(self) -> None:
        """Mark all pending events as persisted.
        
        This should be called after the events have been successfully persisted to the event store.
        It updates the initial version to match the current version and clears the pending events.
        
        This method is thread-safe.
        """
        with self._lock:
            self._initial_version = self._version
            self._pending_events.clear()
            
    def to_snapshot(self) -> 'AggregateSnapshot':
        """Create a snapshot of the aggregate's current state.
        
        Returns:
            An AggregateSnapshot containing the aggregate's state
            
        Raises:
            NotImplementedError: If the aggregate doesn't implement snapshot support
        """
        return self.create_snapshot(self)


class AggregateSnapshot(BaseModel):
    """Base class for aggregate snapshots.
    
    Subclasses should include all the necessary fields to fully restore
    the aggregate's state without replaying all events.
    """
    aggregate_id: UUID
    version: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda dt: dt.isoformat(),
        }
    
    @classmethod
    def from_aggregate(cls, aggregate: AggregateRoot) -> 'AggregateSnapshot':
        """Create a snapshot from an aggregate instance."""
        return cls(
            aggregate_id=aggregate.id,
            version=aggregate.version,
            created_at=aggregate.created_at,
            updated_at=aggregate.updated_at
        )
    
    def __repr__(self) -> str:
        """String representation of the aggregate."""
        return f"{self.__class__.__name__}(id={self.id}, version={self._version})"
