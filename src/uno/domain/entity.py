"""
Entity base class for Uno's DDD model.
"""

from __future__ import annotations
from typing import Any,TypeVar

T_ID = TypeVar("T_ID")


class Entity:
    """
    Uno idiom: Protocol-based entity template for DDD.

    - DO NOT inherit from this class; instead, implement all required attributes/methods from EntityProtocol directly.
    - Inherit from Pydantic's BaseModel if validation/serialization is needed.
    - This class serves as a template/example only.
    - All type checking should use EntityProtocol, not this class.
    """

    # Example attribute required by EntityProtocol
    id: object

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
