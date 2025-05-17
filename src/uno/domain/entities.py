# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
domain.entities
Base entity implementation for Uno framework
"""

from typing import Any
from datetime import datetime, UTC
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class Entity(BaseModel):
    """Base class for domain entities."""
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def update_timestamp(self) -> None:
        """Update the entity's updated_at timestamp."""
        self.updated_at = datetime.now(UTC)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Entity):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
