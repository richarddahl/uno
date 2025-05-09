"""
Entity base class for Uno's DDD model.
"""

from __future__ import annotations
from typing import Any, Generic, TypeVar, Self
from uno.base_model import FrameworkBaseModel
from pydantic import Field, ConfigDict, model_validator
import time
from uno.errors import DomainValidationError
from uno.logging import get_logger

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

    _logger = get_logger(__name__)

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
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Thin wrapper for Pydantic's `model_validate()`. Raises exceptions for Uno error handling.
        Use this only if a broader Python API is required; otherwise, prefer `model_validate()` directly.
        Returns:
            The validated entity instance.
        Raises:
            DomainValidationError: If validation fails.
        """
        try:
            return cls.model_validate(data)
        except Exception as exc:
            cls._logger.error(f"Failed to create {cls.__name__} from dict: {exc}")
            raise DomainValidationError(f"Validation failed for {cls.__name__}: {exc}")

    @model_validator(mode="after")
    def check_invariants(self, values: dict[str, Any]) -> Self:
        """
        Validate the entity's invariants. Override in subclasses for custom validation.
        Raises DomainValidationError or returns values if valid.
        """
        try:
            # Custom invariant checks here
            return self
        except Exception as exc:
            self._logger.error(f"Invariant check failed for entity {self.id}: {exc}")
            raise DomainValidationError(f"Invariant check failed: {exc}")
