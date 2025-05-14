"""
Value object base class for Uno's DDD model.
"""

from __future__ import annotations

from typing import Any, Self

from pydantic import ConfigDict, model_validator

from uno.domain.errors import DomainValidationError
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uno.domain.protocols import ValueObjectProtocol
    from uno.logging.protocols import LoggerProtocol


class ValueObject:
    """
    Uno idiom: Protocol-based value object template for DDD.

    - DO NOT inherit from this class; instead, implement all required attributes/methods from ValueObjectProtocol directly.
    - Inherit from Pydantic's BaseModel if validation/serialization is needed.
    - This class serves as a template/example only.
    - All type checking should use ValueObjectProtocol, not this class.
    """

    # Example method required by ValueObjectProtocol
    def __eq__(self, other: object) -> bool:
        ...
        Compare this value object with another for equality.

        Args:
            other: The object to compare with
            True if the objects are equal, False otherwise
        """
        return self.__eq__(other)

    def __eq__(self, other: Any) -> bool:
        """
        Value objects are equal if their canonical serialization is equal and type matches.
        """
        return isinstance(other, ValueObjectProtocol) and self.model_dump(
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
