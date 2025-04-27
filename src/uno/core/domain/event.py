"""
Public API for Uno Domain Events.

This module re-exports the canonical DomainEvent for user ergonomics.
Always import DomainEvent from uno.core.domain.event, not from events.base_event directly.
"""

from uno.core.events.base_event import DomainEvent

__all__ = ["DomainEvent"]
