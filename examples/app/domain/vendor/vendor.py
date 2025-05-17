# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Domain model and events for Vendor aggregate (Uno example app).

Defines the Vendor aggregate root and its domain events, supporting event sourcing and DDD best practices.
"""

from typing import Self

from pydantic import PrivateAttr, model_validator

from examples.app.domain.vendor.events import VendorCreated, VendorUpdated
from examples.app.domain.vendor.value_objects import EmailAddress
from uno.domain.aggregate import AggregateRoot
from uno.errors.base import get_error_context
from uno.domain.errors import DomainValidationError
from uno.event_bus import DomainEvent


# --- Aggregate ---
class Vendor(AggregateRoot[str]):
    """
    Vendor aggregate root for event-sourced DDD.

    Attributes:
        name: Name of the vendor.
        contact_email: Contact email for the vendor.
        _domain_events: List of domain events to be persisted (private).
    """

    name: str
    contact_email: EmailAddress
    _domain_events: list[DomainEvent] = PrivateAttr(default_factory=list)

    def update(self, name: str, contact_email: EmailAddress) -> None:
        """
        Update the Vendor aggregate and record a VendorUpdated event.

        Args:
            name: New name for the vendor
            contact_email: New contact email for the vendor

        Raises:
            DomainValidationError: If validation fails
        """
        try:
            event = VendorUpdated(
                aggregate_id=self.id,
                vendor_id=self.id,
                name=name,
                contact_email=contact_email,
                version=self.version + 1,
            )
            self._record_event(event)
        except Exception as e:
            if isinstance(e, DomainValidationError):
                raise
            raise DomainValidationError(str(e), details=get_error_context()) from e

    def _record_event(self, event: DomainEvent) -> None:
        """
        Record a domain event for this aggregate and apply it.
        """
        self._domain_events.append(event)
        self._apply_event(event)

    def _apply_event(self, event: DomainEvent) -> None:
        """
        Apply a domain event to mutate aggregate state.
        """
        if isinstance(event, VendorCreated | VendorUpdated):
            self.name = event.name
            self.contact_email = EmailAddress(value=event.contact_email)
        else:
            raise ValueError(f"Unsupported event type: {type(event)}")
