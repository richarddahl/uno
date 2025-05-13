"""
Entity base class for Uno's DDD model.
"""

from __future__ import annotations
from typing import Any, Generic, TypeVar, Self
import time

from pydantic import Field, ConfigDict, model_validator

from uno.base_model import FrameworkBaseModel
from uno.domain.errors import DomainValidationError
from uno.domain.protocols import EntityProtocol
from uno.logging.protocols import LoggerProtocol

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
    - All serialization/deserialization uses Pydantic's built-in methods (`model_dump`, `model_validator`, and 'field_validator' decorated methods).
    - This is the **only** pattern permitted for Uno base models.

    Base class for all DDD entities in Uno.
    Entities have identity, equality by id, and are immutable.

    Example:
        class MyEntity(Entity[int]):
            ...
        data = {"id": 1, ...}
        entity = MyEntity(**data)
    """

    id: T_ID
    created_at: float = Field(default_factory=lambda: time.time())
    updated_at: float = Field(default_factory=lambda: time.time())

    model_config = ConfigDict(frozen=True, extra="forbid")

    _logger: LoggerProtocol | None = None  # Inject via DI or set externally

    def equals(self, other: object) -> bool:
        """
        Compare this entity with another for identity equality.

        Args:
            other: The object to compare with

        Returns:
            True if the objects have the same identity, False otherwise
        """
        return self.__eq__(other)

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

    @model_validator(mode="after")
    async def check_invariants(self, values: dict[str, Any]) -> Self:
        """
        Validate the entity's invariants. Override in subclasses for custom validation.
        Raises DomainValidationError or returns values if valid.
        """
        try:
            # Custom invariant checks here
            return self
        except Exception as exc:
            if self._logger:
                await self._logger.error(
                    f"Invariant check failed for entity {self.id}: {exc}"
                )
            raise DomainValidationError(f"Invariant check failed: {exc}")
