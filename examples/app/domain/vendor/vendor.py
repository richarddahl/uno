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
from uno.events import DomainEvent


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

    @classmethod
    def create(cls, vendor_id: str, name: str, contact_email: EmailAddress) -> Self:
        """
        Create a new Vendor aggregate and record a VendorCreated event.

        Args:
            vendor_id: Unique identifier for the vendor
            name: Name of the vendor
            contact_email: Contact email for the vendor

        Returns:
            A new Vendor instance

        Raises:
            DomainValidationError: If validation fails
        """
        try:
            if not vendor_id:
                raise DomainValidationError(
                    "vendor_id is required", details=get_error_context()
                )
            if not name:
                raise DomainValidationError(
                    "name is required", details=get_error_context()
                )
            if not contact_email:
                raise DomainValidationError(
                    "contact_email is required", details=get_error_context()
                )
            vendor = cls(id=vendor_id, name=name, contact_email=contact_email)
            # Convert EmailAddress to string for event data
            email_str = contact_email.value if hasattr(contact_email, 'value') else contact_email
            event_data = {
                "vendor_id": vendor_id,
                "name": name,
                "contact_email": email_str,
                "version": 1,
                "aggregate_id": vendor_id  # Add aggregate_id for the event
            }
            event = VendorCreated.from_dict(event_data)
            vendor._record_event(event)
            return vendor
        except Exception as e:
            if isinstance(e, DomainValidationError):
                raise
            raise DomainValidationError(str(e), details=get_error_context()) from e

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
            if not name:
                raise DomainValidationError(
                    "name is required", details=get_error_context()
                )
            if not contact_email:
                raise DomainValidationError(
                    "contact_email is required", details=get_error_context()
                )
            event_data = {
                "vendor_id": self.id,
                "name": name,
                "contact_email": contact_email,
                "version": 1,
            }
            event = VendorUpdated.from_dict(event_data)
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

    @model_validator(mode="after")
    def check_invariants(self) -> Self:
        """
        Validate the aggregate's invariants. Raises ValueError if invalid, returns self if valid.
        """
        if not self.name or not isinstance(self.name, str):
            raise ValueError("name must be a non-empty string")
        if not self.contact_email or not isinstance(self.contact_email, EmailAddress):
            raise ValueError("contact_email must be an EmailAddress value object")
        # Add more invariants as needed
        return self
