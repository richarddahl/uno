"""
Entity base class for Uno's DDD model.
"""
from __future__ import annotations
from typing import Any, Generic, TypeVar, Self
from pydantic import BaseModel, Field, ConfigDict

T_ID = TypeVar("T_ID")

class Entity(BaseModel, Generic[T_ID]):
    """
    Uno canonical Pydantic base model for all entities.

    - All model-wide concerns (e.g., immutability, validation) are handled via Pydantic model_config and validators.
    - All type hints use modern Python syntax (str, int, dict[str, Any], Self, etc.).
    - All serialization/deserialization uses Pydantic's built-in methods (`model_dump`, `model_validate`).
    - If broader Python idioms are needed, thin wrappers (e.g., to_dict, from_dict) are provided that simply call the canonical Pydantic methods.
    - This is the **only** pattern permitted for Uno base models.

    Base class for all DDD entities in Uno.
    Entities have identity, equality by id, and are immutable.
    """
    id: T_ID
    created_at: float = Field(default_factory=lambda: __import__('time').time())
    updated_at: float = Field(default_factory=lambda: __import__('time').time())

    model_config = ConfigDict(frozen=True, extra="forbid")

    def __eq__(self, other: Any) -> bool:
        """
        Entities are equal if their id is equal and type matches.
        """
        return isinstance(other, Entity) and self.id == other.id

    def __hash__(self) -> int:
        """
        Hash is based on the entity id.
        """
        return hash(self.id)

    def to_dict(self) -> dict[str, Any]:
        """
        Thin wrapper for Pydantic's `model_dump()`.
        Use this only if a broader Python API is required; otherwise, prefer `model_dump()` directly.
        """
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Thin wrapper for Pydantic's `model_validate()`.
        Use this only if a broader Python API is required; otherwise, prefer `model_validate()` directly.
        """
        return cls.model_validate(data)
