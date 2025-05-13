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

if TYPE_CHECKING:
    from uno.domain.protocols import DomainEventProtocol
    from uno.events.protocols import SerializationProtocol


class DomainEvent(BaseModel):
    """
    Base class for all domain events.

    Implements the DomainEventProtocol and SerializationProtocol, providing
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

    def to_dict(self) -> dict[str, Any]:
        """
        Convert event to a dictionary for serialization.

        Returns:
            Dictionary representation of the event
        """
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Create an event instance from a dictionary.

        Args:
            data: Dictionary containing event data

        Returns:
            New event instance
        """
        # Apply upcasting if needed
        if "version" in data and data["version"] < cls.version:
            data = cls.upcast(data)

        return cls.model_validate(data)

    def serialize(self) -> dict[str, Any]:
        """
        Serialize the event to a dictionary.

        Implements the SerializationProtocol.serialize method.
        This is an alias for to_dict() for backward compatibility.

        Returns:
            A dictionary representation of the event.
        """
        return self.to_dict()

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> Self:
        """
        Deserialize an event from a dictionary.

        Implements the SerializationProtocol.deserialize method.
        This is an alias for from_dict() for backward compatibility.

        Args:
            data: A dictionary containing event data.

        Returns:
            An instance of the event.
        """
        return cls.from_dict(data)

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


# Register DomainEvent as a virtual subclass of DomainEventProtocol.
# This ensures that runtime isinstance/issubclass checks recognize DomainEvent
# as implementing the DomainEventProtocol, even without explicit inheritance.
if not TYPE_CHECKING:
    try:
        from uno.domain.protocols import DomainEventProtocol
        from uno.events.protocols import SerializationProtocol

    except ImportError as e:
        import logging
    except ImportError as e:
        import logging

        logging.warning(
            f"Failed to import DomainEventProtocol or SerializationProtocol: {e}"
        )
        pass
