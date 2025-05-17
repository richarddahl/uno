# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
domain.events
Base domain event implementation for Uno framework
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, ClassVar, Self, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Type variable for event state
S = TypeVar("S")


class DomainEvent(BaseModel):
    """Base class for all domain events.

    Domain events represent something that happened in the domain that domain
    experts care about. They are immutable and represent facts that have occurred.
    """

    # Public properties that are part of the event interface
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    aggregate_id: UUID | None = None
    aggregate_type: str | None = None
    aggregate_version: int | None = None
    occurred_on: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)
    state: dict[str, Any] = Field(default_factory=dict)

    # Model configuration
    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True,  # Events are immutable
        arbitrary_types_allowed=True,
        populate_by_name=True,
        validate_assignment=True,
    )

    def __init__(self, **data: Any) -> None:
        """Initialize a domain event with the given data."""
        super().__init__(**data)
        # Any other initialization logic can go here

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Create a domain event from a dictionary."""
        return cls.model_validate(data)

    @classmethod
    def create(cls, **kwargs: Any) -> Self:
        """Create a new domain event."""
        return cls(**kwargs)

    @field_validator("event_type", mode="before")
    @classmethod
    def validate_event_type(cls, v: Any) -> str:
        """Validate the event type."""
        if isinstance(v, str) and v:
            return v
        return cls.__name__
