# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Canonical event base for Uno's DDD/event sourcing system.
All domain/integration events should inherit from this class.
"""

from __future__ import annotations

import json
import time
import uuid
import decimal
import enum
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, Self

from pydantic import Field, ConfigDict
from uno.base_model import FrameworkBaseModel
from uno.logging import get_logger

if TYPE_CHECKING:
    from uno.services.hash_service_protocol import HashServiceProtocol


logger = get_logger(__name__)

# Global registry of event classes
_EVENT_CLASSES: dict[str, type[DomainEvent]] = {}


class EventMetadata(FrameworkBaseModel):
    """
    Standard metadata for domain events in Uno Framework.

    This class represents standard metadata that should be included with all events.
    """

    created_at: float = Field(
        default_factory=time.time,
        description="Unix timestamp when the event was created",
    )
    correlation_id: str | None = Field(
        default=None, description="ID linking related events in a flow"
    )
    causation_id: str | None = Field(
        default=None, description="ID of the event that caused this event"
    )
    user_id: str | None = Field(
        default=None, description="ID of the user who triggered this event"
    )
    source: str | None = Field(
        default=None, description="Source system that generated the event"
    )

    model_config = ConfigDict(
        frozen=True,  # Events are immutable
        json_encoders={
            decimal.Decimal: lambda v: float(v),
            uuid.UUID: lambda v: str(v),
            enum.Enum: lambda v: v.value,
        },
    )


# Base class for all domain events
class DomainEvent:
    """
    Base class for all domain events in Uno Framework.

    This class provides common functionality for all domain events:
    - Event registration/discovery
    - Event versioning
    - Event serialization (to_dict)
    - Event deserialization (upcast/from_dict)
    - Tampering detection (event_hash)

    All domain events must have:
    - event_id: Unique ID for each event instance
    - aggregate_id: ID of the aggregate this event belongs to
    - event_type: Type name for this event class
    - version: Schema version for this event (enables upcasting)
    """

    event_id: str
    aggregate_id: str
    event_type: ClassVar[str]
    version: int = 1
    event_hash: str | None = None
    metadata: EventMetadata | None = None

    _registered: ClassVar[bool] = False

    def __init__(self):
        """
        Initialize a new domain event with a unique ID.

        Each event instance gets a unique event_id. The aggregate_id
        must be set by the subclass to identify which entity/aggregate
        this event applies to.
        """
        self.event_id = str(uuid.uuid4())
        self.event_hash = None  # Initialized later when needed

    def __init_subclass__(cls, **kwargs):
        """
        Automatically register event subclasses in the global registry.

        This allows events to be dynamically discovered and reconstructed
        from serialized form.
        """
        super().__init_subclass__(**kwargs)

        if not hasattr(cls, "event_type"):
            cls.event_type = cls.__name__

        if not cls._registered and cls.event_type:
            if cls.event_type in _EVENT_CLASSES:
                logger.warning(
                    f"Event type '{cls.event_type}' is already registered. "
                    f"Overwriting previous registration."
                )

            _EVENT_CLASSES[cls.event_type] = cls
            cls._registered = True

    def to_dict(self) -> dict[str, Any]:
        """
        Convert event to a dictionary for serialization.

        Override this in subclasses if needed for custom serialization.

        Returns:
            Dictionary representation of the event
        """
        # Get all attributes except private ones
        result = {
            key: value
            for key, value in self.__dict__.items()
            if not key.startswith("_") and key != "metadata"
        }

        # Include metadata if present
        if hasattr(self, "metadata") and self.metadata:
            result["metadata"] = self.metadata.model_dump()

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Create an event instance from a dictionary.

        Args:
            data: Dictionary containing event data

        Returns:
            New event instance

        Raises:
            ValueError: If the data doesn't match the expected format
        """
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {type(data)}")

        instance = cls()

        # Copy all fields from dict to object
        for key, value in data.items():
            if key != "metadata":
                setattr(instance, key, value)

        # Handle metadata separately
        if "metadata" in data and data["metadata"]:
            instance.metadata = EventMetadata.model_validate(data["metadata"])

        return instance

    @classmethod
    def get_event_class(cls, event_type: str) -> type[DomainEvent]:
        """
        Get the event class for a given event type.

        Args:
            event_type: The type string for the event

        Returns:
            Event class

        Raises:
            ValueError: If the event type is not registered
        """
        if event_type not in _EVENT_CLASSES:
            raise ValueError(f"Unknown event type: {event_type}")
        return _EVENT_CLASSES[event_type]

    @classmethod
    def upcast(cls, data: dict[str, Any]) -> DomainEvent:
        """
        Upgrade an event from an older version to the current version.

        This method handles event schema migrations by applying transformations
        to update the event data to the latest schema version.

        Args:
            data: Dictionary containing event data

        Returns:
            Upcasted event instance

        Raises:
            ValueError: If the event type is not registered or upcast fails
        """
        if "event_type" not in data:
            raise ValueError("Event data missing 'event_type' field")

        event_type = data["event_type"]

        try:
            event_class = cls.get_event_class(event_type)
            return event_class.from_dict(data)
        except Exception as e:
            raise ValueError(f"Failed to upcast event: {e}") from e

    def calculate_hash(self, hash_service: HashServiceProtocol) -> str:
        """
        Calculate a hash for this event using the provided hash service.

        This hash can be used to verify event integrity and detect tampering.

        Args:
            hash_service: Service for generating cryptographic hashes

        Returns:
            Hash string for the event
        """
        # Get serialized event data excluding the hash itself
        event_data = self.to_dict()
        if "event_hash" in event_data:
            del event_data["event_hash"]

        # Convert to a stable string representation
        sorted_json = json.dumps(event_data, sort_keys=True)

        # Calculate hash
        return hash_service.hash_string(sorted_json)
