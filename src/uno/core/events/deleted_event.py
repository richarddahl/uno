"""
DeletedEvent for Uno event sourcing soft delete pattern.
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import ConfigDict, Field

from uno.core.events.base_event import DomainEvent


class DeletedEvent(DomainEvent):
    """
    Event representing the soft deletion of an aggregate.
    """

    event_type: ClassVar[str] = "deleted"
    aggregate_id: str = Field(..., description="ID of the deleted aggregate.")
    reason: str | None = Field(default=None, description="Reason for deletion, if any.")
    deleted_by: str | None = Field(
        default=None, description="Who performed the deletion."
    )

    model_config = ConfigDict(frozen=True)
