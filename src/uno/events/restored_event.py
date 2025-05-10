"""
RestoredEvent for Uno event sourcing restore/undelete pattern.
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import ConfigDict, Field

from uno.events.base_event import DomainEvent


class RestoredEvent(DomainEvent):
    """
    Event representing the restoration (undelete) of an aggregate.

    Note: After creating a RestoredEvent instance, always call set_event_hash() before saving or publishing.
    """

    event_type: ClassVar[str] = "restored"
    aggregate_id: str = Field(
        ...,
        description="ID of the restored aggregate.",
        validation_alias="AGGREGATE_ID"
    )
    restored_by: str | None = Field(
        default=None,
        description="Who performed the restoration.",
        validation_alias="RESTORED_BY"
    )
    reason: str | None = Field(
        default=None,
        description="Reason for restoration, if any.",
        validation_alias="REASON"
    )

    model_config = ConfigDict(frozen=True)
