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
    Base class for all domain events.

    Implements the DomainEventProtocol, providing
    common functionality for all domain events in the system. Domain events:

    1. Are immutable records of something that happened in the domain
    2. Contain all the data needed to understand what happened
    3. Include metadata like timestamps and correlation IDs
    4. Support versioning for schema evolution
    5. Support serialization for persistence and transport

    All domain events in the Uno framework should inherit from this class
    to ensure consistency and compatibility with the event system.
    """

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    aggregate_id: str
    event_type: ClassVar[str] = "DomainEvent"
    version: int = 1
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        frozen=True,
        from_attributes=True,
    )

    @classmethod
    def upcast(cls, data: dict[str, Any]) -> dict[str, Any]:
        """
        Upcast event data from an older version to the current version.

        Transforms event data from older schema versions to the current version.
        This method implements a recursive upcasting approach where events are
        incrementally upcasted from one version to the next until reaching the
        current version.

        Args:
            data: Event data in an older schema version

        Returns:
            Event data transformed to the current schema version

        Example:
            ```python
            class UserEmailChanged(DomainEvent):
                event_type: ClassVar[str] = "UserEmailChanged"
                version: int = 2
                user_id: str
                email: str
                verified: bool = False  # Added in v2

                @classmethod
                def _upcast_v1_to_v2(cls, data: dict[str, Any]) -> dict[str, Any]:
                    result = data.copy()
                    result["verified"] = False
                    return result
            ```
        """
        version = data.get("version", 1)

        # Call appropriate upcasting function based on version
        if version < cls.version:
            upcast_method = f"_upcast_v{version}_to_v{version + 1}"
            upcast_func = getattr(cls, upcast_method, None)

            if upcast_func:
                data = upcast_func(data)
                data["version"] = version + 1
                # Recursively upcast if needed
                return cls.upcast(data)

        return data

    def __str__(self) -> str:
        """Return a string representation of the event."""
        return f"{self.__class__.__name__}({self.event_id[:8]}...)"

    def __repr__(self) -> str:
        """Return a detailed string representation of the event."""
        return (
            f"{self.__class__.__name__}("
            f"event_id='{self.event_id}', "
            f"aggregate_id='{self.aggregate_id}', "
            f"version={self.version})"
        )
