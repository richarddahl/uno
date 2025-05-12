"""
Uno Event Serialization/Deserialization
- Versioning (default)
- Pydantic v2 models for event data validation/serialization
- Canonical Uno serialization contract
"""

from __future__ import annotations
from typing import ClassVar, Any
from pydantic import BaseModel, ValidationError
from uno.events.errors import EventSerializationError, EventDeserializationError


class SerializableEvent(BaseModel):
    """
    Base class for serializable events.

    Provides standardized serialization/deserialization with proper error handling.
    Implements Uno canonical contract for event serialization.
    """

    event_type: ClassVar[str]
    version: int

    def serialize(self) -> dict[str, Any]:
        """
        Serialize the event to a dict using Uno canonical contract.
        Raises EventSerializationError on failure.
        """
        try:
            return self.model_dump(exclude_none=True, exclude_unset=True, by_alias=True)
        except Exception as exc:
            raise EventSerializationError(
                f"Failed to serialize event: {exc!s}"
            ) from exc

    @classmethod
    def deserialize(
        cls: type[SerializableEvent], data: dict[str, Any]
    ) -> SerializableEvent:
        """
        Deserialize event from dict using Uno canonical contract.
        Raises EventDeserializationError on failure.
        """
        try:
            return cls.model_validate(data)
        except ValidationError as exc:
            raise EventDeserializationError(
                f"Failed to deserialize event: {exc!s}"
            ) from exc

    # Pydantic v2 config for Uno contract
    model_config = {
        "use_enum_values": True,
        "str_strip_whitespace": True,
        "validate_assignment": True,
    }


# TODO: Add extensible registry, custom field aliases, custom serializers, etc. as needed
