"""
Canonical event base for Uno's DDD/event sourcing system.
All domain/integration events should inherit from this class.
"""
from __future__ import annotations
from typing import Any, ClassVar
from pydantic import BaseModel, Field

class DomainEvent(BaseModel):
    """
    Base class for all domain and integration events in Uno.
    Events are immutable and serializable.
    """
    event_id: str = Field(default_factory=lambda: "evt_" + __import__('uuid').uuid4().hex)
    event_type: ClassVar[str] = "domain_event"
    timestamp: float = Field(default_factory=lambda: __import__('time').time())
    correlation_id: str | None = None
    causation_id: str | None = None
    metadata: dict[str, Any] = {}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DomainEvent:
        return cls.model_validate(data)

    class Config:
        frozen = True
        extra = "forbid"
