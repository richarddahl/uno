"""
Entity base class for Uno's DDD model.
"""
from __future__ import annotations
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

T_ID = TypeVar("T_ID")

class Entity(BaseModel, Generic[T_ID]):
    """
    Base class for entities with identity and equality semantics.
    """
    id: T_ID
    created_at: float = Field(default_factory=lambda: __import__('time').time())
    updated_at: float = Field(default_factory=lambda: __import__('time').time())

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Entity) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Config:
        frozen = True
        extra = "forbid"
