"""
Value object base class for Uno's DDD model.
"""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel

class ValueObject(BaseModel):
    """
    Base class for value objects (immutable, equality by value).
    """
    def __eq__(self, other: Any) -> bool:
        return isinstance(other, ValueObject) and self.model_dump() == other.model_dump()

    def __hash__(self) -> int:
        return hash(tuple(sorted(self.model_dump().items())))

    class Config:
        frozen = True
        extra = "forbid"
