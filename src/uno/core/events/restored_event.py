"""
RestoredEvent for Uno event sourcing restore/undelete pattern.
"""

from __future__ import annotations
from typing import ClassVar
from pydantic import Field, ConfigDict
from uno.core.events.base_event import DomainEvent


class RestoredEvent(DomainEvent):
    """
    Event representing the restoration (undelete) of an aggregate.

    Note: After creating a RestoredEvent instance, always call set_event_hash() before saving or publishing.
    """

    event_type: ClassVar[str] = "restored"
    aggregate_id: str = Field(..., description="ID of the restored aggregate.")
    restored_by: str | None = Field(
        default=None, description="Who performed the restoration."
    )
    reason: str | None = Field(
        default=None, description="Reason for restoration, if any."
    )

    model_config = ConfigDict(frozen=True)
