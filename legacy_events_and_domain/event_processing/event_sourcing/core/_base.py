"""
Base event class for domain events.

This module provides the base implementation of the DomainEventProtocol.
Domain events represent facts that have happened in the domain and are
immutable once created. They are the core of event sourcing and event-driven
architectures in the Uno framework.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar, Self
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class DomainEvent(BaseModel):
    """
    Base class for all domain events in the Uno framework.
    
    This class provides default implementations for common event functionality
    and serves as the base for all domain events. It implements the DomainEventProtocol.
    
    Attributes:
        event_id: Unique identifier for the event
        aggregate_id: Identifier of the aggregate this event belongs to
        event_type: Type identifier for the event (class variable)
        version: Version of the event schema
        timestamp: When the event occurred
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    aggregate_id: str
    event_type: ClassVar[str] = "DomainEvent"
    version: int = 1
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def upcast(cls, data: dict[str, Any]) -> dict[str, Any]:
        """
        Upcast event data from an older version to the current version.
        See Uno documentation for versioning/upcasting idioms.
        """
        version = data.get("version", 1)
        if version < getattr(cls, "version", 1):
            upcast_method = f"_upcast_v{version}_to_v{version + 1}"
            upcast_func = getattr(cls, upcast_method, None)
            if upcast_func:
                data = upcast_func(data)
                data["version"] = version + 1
                return cls.upcast(data)
        return data

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({getattr(self, 'event_id', '')[:8]}...)"


        
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"event_id='{getattr(self, 'event_id', '')}', "
            f"aggregate_id='{getattr(self, 'aggregate_id', '')}', "
            f"version={getattr(self, 'version', '')})"
        )
