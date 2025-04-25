"""
Base domain event types to avoid circular imports.

This module defines the minimal interfaces needed by both core domain
and event system modules to avoid circular imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar


@dataclass
class BaseDomainEvent:
    """
    Base class for all domain events with essential fields.
    
    This is a minimal version used to avoid circular imports between
    uno.core.domain.core and uno.core.events.events.
    """
    
    event_id: str
    event_type: ClassVar[str]
    timestamp: datetime | None = None
    version: int = 1
    aggregate_id: str | None = None
    aggregate_type: str | None = None
    topic: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
