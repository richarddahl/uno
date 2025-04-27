# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Domain model and events for Vendor aggregate (Uno example app).

Defines the Vendor aggregate root and its domain events, supporting event sourcing and DDD best practices.
"""
from uno.core.domain.aggregate import AggregateRoot
from uno.core.domain.event import DomainEvent
from pydantic import PrivateAttr
from typing import Self

# --- Events ---
class VendorCreated(DomainEvent):
    """
    Event representing the creation of a Vendor aggregate.
    Attributes:
        vendor_id: Unique identifier for the vendor.
        name: Name of the vendor.
        contact_email: Contact email for the vendor.
    """
    vendor_id: str
    name: str
    contact_email: str

class VendorUpdated(DomainEvent):
    """
    Event representing an update to a Vendor aggregate.
    Attributes:
        vendor_id: Unique identifier for the vendor.
        name: Updated name.
        contact_email: Updated contact email.
    """
    vendor_id: str
    name: str
    contact_email: str

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
    contact_email: str
    _domain_events: list[DomainEvent] = PrivateAttr(default_factory=list)

    @classmethod
    def create(cls, vendor_id: str, name: str, contact_email: str) -> Self:
        """
        Create a new Vendor aggregate and record a VendorCreated event.

        Args:
            vendor_id: Unique vendor ID.
            name: Vendor name.
            contact_email: Vendor contact email.
        Returns:
            Vendor: The created Vendor aggregate.
        """
        vendor = cls(id=vendor_id, name=name, contact_email=contact_email)
        event = VendorCreated(vendor_id=vendor_id, name=name, contact_email=contact_email)
        vendor._record_event(event)
        return vendor

    def update(self, name: str, contact_email: str) -> None:
        """
        Update the Vendor aggregate and record a VendorUpdated event.

        Args:
            name: New vendor name.
            contact_email: New contact email.
        """
        event = VendorUpdated(vendor_id=self.id, name=name, contact_email=contact_email)
        self._record_event(event)

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
        if isinstance(event, VendorCreated):
            self.name = event.name
            self.contact_email = event.contact_email
        elif isinstance(event, VendorUpdated):
            self.name = event.name
            self.contact_email = event.contact_email
