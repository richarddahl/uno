"""
Value object base class for Uno's DDD model.
"""

from __future__ import annotations

from typing import Any, Self, final

from pydantic import BaseModel, ConfigDict


@final
class ValueObject(BaseModel):
    """
    Uno canonical Pydantic base model for all value objects.

    Value objects are strictly immutable and compared by value (not identity).
    Canonical serialization contract:
      - Always use `model_dump(exclude_none=True, exclude_unset=True, by_alias=True)` for serialization, hashing, and transport.
      - Unset and None fields are treated identically; excluded from serialization and hashing.
      - This contract is enforced by dedicated tests.

    - All model-wide concerns (e.g., immutability, validation) are handled via Pydantic model_config and validators.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    def to_dict(self) -> dict[str, Any]:
        """
        Returns the canonical dict representation using Uno contract.
        """
        return self.model_dump(exclude_none=True, exclude_unset=True, by_alias=True)

    @classmethod
    def from_dict(cls: type[Self], data: dict[str, Any]) -> Self:
        """
        Creates a value object from a dict using the Uno contract.
        """
        return cls.model_validate(data)

    def __eq__(self, other: Any) -> bool:
        """
        Value objects are equal if their canonical serialization is equal and type matches.
        """
        return isinstance(other, ValueObject) and self.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True
        ) == other.model_dump(exclude_none=True, exclude_unset=True, by_alias=True)

    def __hash__(self) -> int:
        """
        Hash is based on the canonical serialization contract (Uno standard).
        """
        return hash(
            tuple(
                sorted(
                    self.model_dump(
                        exclude_none=True, exclude_unset=True, by_alias=True
                    ).items()
                )
            )
        )
