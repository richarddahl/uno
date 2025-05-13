"""
Value object base class for Uno's DDD model.
"""

from __future__ import annotations

from typing import Any, Self

from pydantic import ConfigDict, model_validator

from uno.base_model import FrameworkBaseModel
from uno.domain.errors import DomainValidationError
from uno.domain.protocols import ValueObjectProtocol
from uno.logging.protocols import LoggerProtocol


class ValueObject(FrameworkBaseModel):
    """
    Uno canonical Pydantic base model for all value objects.

    Value objects are strictly immutable and compared by value (not identity).
    Canonical serialization contract:
      - Always use `model_dump(exclude_none=True, exclude_unset=True, by_alias=True)` for serialization, hashing, and transport.
      - Unset and None fields are treated identically; excluded from serialization and hashing.
      - This contract is enforced by dedicated tests.

    - All model-wide concerns (e.g., immutability, validation) are handled via Pydantic model_config and validators.

    Example:
        class Money(ValueObject):
            amount: int
            currency: str
        data = {"amount": 100, "currency": "USD"}
        try:
            money = Money(**data)
        except ValidationError as e:
            # handle error
            ...
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    _logger: LoggerProtocol | None = None  # Inject via DI or set externally

    def equals(self, other: object) -> bool:
        """
        Compare this value object with another for equality.

        Args:
            other: The object to compare with

        Returns:
            True if the objects are equal, False otherwise
        """
        return self.__eq__(other)

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
