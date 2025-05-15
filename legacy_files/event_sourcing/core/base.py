"""Core event classes and functionality.

This module contains the fundamental building blocks for events in the Uno framework,
including base classes and standard event implementations.
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional, Type, TypeVar, Union
from datetime import datetime
import uuid

from pydantic import BaseModel, Field, field_serializer, ConfigDict

# Re-export commonly used types for backward compatibility
__all__ = [
    'DomainEvent',
    'EventMetadata',
    'EventEnvelope',
    'EventStream',
    'EventStreamSlice',
    'EventType',
    'EventData',
]

# Type variables for generic event handling
T = TypeVar('T', bound='DomainEvent')
EventType = Type['DomainEvent']
EventData = Dict[str, Any]


class EventMetadata(BaseModel):
    """Metadata associated with domain events.
    
    Attributes:
        event_id: Unique identifier for the event
        timestamp: When the event occurred
        correlation_id: For tracing related events
        causation_id: The event that caused this event
        user_id: ID of the user who triggered the event
        source: Source system or service
        version: Event schema version
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    user_id: Optional[str] = None
    source: Optional[str] = None
    version: str = "1.0"
    
    # Additional custom metadata
    custom: Dict[str, Any] = Field(default_factory=dict)


class DomainEvent(BaseModel):
    """Base class for all domain events.
    
    All domain events should inherit from this class. It provides common
    functionality like metadata handling and serialization.
    
    Attributes:
        metadata: Event metadata
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # Class-level attributes
    event_type: ClassVar[str]
    
    # Instance attributes
    metadata: EventMetadata = Field(default_factory=EventMetadata)
    
    def __init_subclass__(cls, **kwargs):
        """Automatically set event_type if not explicitly defined."""
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, 'event_type') or not cls.event_type:
            cls.event_type = f"{cls.__module__}.{cls.__qualname__}"
    
    @property
    def event_id(self) -> str:
        """Get the event's unique identifier."""
        return self.metadata.event_id
    
    @property
    def timestamp(self) -> datetime:
        """Get when the event occurred."""
        return self.metadata.timestamp
    
    def with_metadata(self, **kwargs) -> 'DomainEvent':
        """Create a copy of this event with updated metadata."""
        new_metadata = self.metadata.model_copy(update=kwargs)
        return self.model_copy(update={'metadata': new_metadata})
    
    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """Create an event from a dictionary."""
        if 'metadata' in data and isinstance(data['metadata'], dict):
            data['metadata'] = EventMetadata(**data['metadata'])
        return cls.model_validate(data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the event to a dictionary."""
        return self.model_dump(mode='json')


class EventEnvelope(BaseModel):
    """Container for events with metadata and type information."""
    event_type: str
    event_data: Dict[str, Any]
    metadata: EventMetadata
    
    @classmethod
    def wrap(cls, event: DomainEvent) -> 'EventEnvelope':
        """Wrap an event in an envelope."""
        return cls(
            event_type=event.__class__.__name__,
            event_data=event.model_dump(exclude={'metadata'}),
            metadata=event.metadata
        )
    
    def unwrap(self, event_type: Type[T]) -> T:
        """Unwrap the event from the envelope."""
        event = event_type(**self.event_data)
        event.metadata = self.metadata
        return event


class EventStream:
    """A sequence of domain events with versioning support."""
    
    def __init__(self, stream_id: str, events: Optional[List[DomainEvent]] = None) -> None:
        self.stream_id = stream_id
        self._events: List[DomainEvent] = list(events) if events else []
    
    def append(self, event: DomainEvent) -> None:
        """Add an event to the stream.
        
        Args:
            event: The domain event to add to the stream
        """
        self._events.append(event)
    
    def __iter__(self) -> 'EventStream':
        """Return an iterator over the events in the stream."""
        return iter(self._events)
    
    def __len__(self) -> int:
        """Return the number of events in the stream."""
        return len(self._events)
    
    def __getitem__(self, index: int) -> DomainEvent:
        """Get an event by index.
        
        Args:
            index: The index of the event to retrieve
            
        Returns:
            The domain event at the specified index
            
        Raises:
            IndexError: If the index is out of range
        """
        return self._events[index]


class EventStreamSlice:
    """A slice of an event stream with version information."""
    
    def __init__(
        self,
        stream_id: str,
        events: List[DomainEvent],
        from_version: int = 0,
        to_version: Optional[int] = None
    ):
        self.stream_id = stream_id
        self.events = events
        self.from_version = from_version
        self.to_version = to_version if to_version is not None else (from_version + len(events) - 1)
