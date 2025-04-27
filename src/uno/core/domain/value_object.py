"""
Value object base class for Uno's DDD model.
"""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Any, Self

class ValueObject(BaseModel):
    """
    Uno canonical Pydantic base model for all value objects.

    Canonical serialization contract:
      - Always use `model_dump(exclude_none=True, exclude_unset=True, by_alias=True, sort_keys=True)` for serialization, hashing, and transport.
      - Unset and None fields are treated identically; excluded from serialization and hashing.
      - This contract is enforced by dedicated tests.
    
    - All model-wide concerns (e.g., immutability, validation) are handled via Pydantic model_config and validators.
    - All type hints use modern Python syntax (str, int, dict[str, Any], Self, etc.).
    - All serialization/deserialization uses Pydantic's built-in methods (`model_dump`, `model_validate`).
    - If broader Python idioms are needed, thin wrappers (e.g., to_dict, from_dict) are provided that simply call the canonical Pydantic methods.
    - This is the **only** pattern permitted for Uno base models.

    Base class for all DDD value objects in Uno.
    Value objects are immutable and compared by value.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    def __eq__(self, other: Any) -> bool:
        """
        Value objects are equal if their canonical serialization is equal and type matches.
        """
        return (
            isinstance(other, ValueObject)
            and self.model_dump(exclude_none=True, exclude_unset=True, by_alias=True)
            == other.model_dump(exclude_none=True, exclude_unset=True, by_alias=True)
        )

    def __hash__(self) -> int:
        """
        Hash is based on the canonical serialization contract (Uno standard).
        """
        return hash(tuple(sorted(self.model_dump(exclude_none=True, exclude_unset=True, by_alias=True).items())))

    def to_dict(self) -> dict[str, Any]:
        """
        Canonical serialization: returns dict using Uno contract.
        Uses model_dump(exclude_none=True, exclude_unset=True, by_alias=True).
        """
        return self.model_dump(exclude_none=True, exclude_unset=True, by_alias=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Thin wrapper for Pydantic's `model_validate()`.
        Use this only if a broader Python API is required; otherwise, prefer `model_validate()` directly.
        """
        return cls.model_validate(data)
