"""
Entity base class for Uno's DDD model.
"""
from __future__ import annotations
from typing import Any, Generic, TypeVar, Self
from uno.core.base_model import FrameworkBaseModel
from pydantic import Field, ConfigDict, model_validator
from uno.core.errors.result import Success, Failure
import time

T_ID = TypeVar("T_ID")

class Entity(FrameworkBaseModel, Generic[T_ID]):
    """
    Uno canonical Pydantic base model for all entities.

    Canonical serialization contract:
      - Always use `model_dump(exclude_none=True, exclude_unset=True, by_alias=True, sort_keys=True)` for serialization, hashing, and transport.
      - Unset and None fields are treated identically; excluded from serialization and hashing.
      - This contract is enforced by dedicated tests.
    
    - All model-wide concerns (e.g., immutability, validation) are handled via Pydantic model_config and validators.
    - All type hints use modern Python syntax (str, int, dict[str, Any], Self, etc.).
    - All serialization/deserialization uses Pydantic's built-in methods (`model_dump`, `model_validate`).
    - If broader Python idioms are needed, thin wrappers (e.g., to_dict, from_dict) are provided that simply call the canonical Pydantic methods.
    - This is the **only** pattern permitted for Uno base models.

    Base class for all DDD entities in Uno.
    Entities have identity, equality by id, and are immutable.

    Example:
        class MyEntity(Entity[int]):
            ...
        data = {"id": 1, ...}
        result = MyEntity.from_dict(data)
        if isinstance(result, Success):
            entity = result.value
        else:
            # handle error
            ...
    """
    id: T_ID
    created_at: float = Field(default_factory=lambda: time.time())
    updated_at: float = Field(default_factory=lambda: time.time())

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
        Canonical serialization: returns dict using Uno contract.
        Uses model_dump(exclude_none=True, exclude_unset=True, by_alias=True).
        """
        return self.model_dump(exclude_none=True, exclude_unset=True, by_alias=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Success[Self, Exception] | Failure[Self, Exception]:
        """
        Thin wrapper for Pydantic's `model_validate()`. Returns Result for Uno error handling.
        Use this only if a broader Python API is required; otherwise, prefer `model_validate()` directly.
        Returns:
            Success[Self, Exception](entity) if valid, Failure[Self, Exception](error) otherwise.
        """
        try:
            return Success[Self, Exception](cls.model_validate(data))
        except Exception as exc:
            return Failure[Self, Exception](Exception(f"Failed to create {cls.__name__} from dict: {exc}"))

    def validate(self) -> Success[None, Exception] | Failure[None, Exception]:
        """
        Validate the entity's invariants. Override in subclasses for custom validation.
        Returns:
            Success[None, Exception](None) if valid, Failure[None, Exception](error) otherwise.
        """
        return Success[None, Exception](None)
