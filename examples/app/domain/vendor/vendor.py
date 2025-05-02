# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Domain model and events for Vendor aggregate (Uno example app).

Defines the Vendor aggregate root and its domain events, supporting event sourcing and DDD best practices.
"""

from typing import Self

from pydantic import PrivateAttr

from examples.app.domain.value_objects import EmailAddress
from examples.app.domain.vendor.events import VendorCreated, VendorUpdated
from uno.core.domain.aggregate import AggregateRoot
from uno.core.domain.event import DomainEvent
from uno.core.errors.base import get_error_context
from uno.core.errors.definitions import DomainValidationError
from uno.core.errors.result import Failure, Success


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
    def create(
        cls, vendor_id: str, name: str, contact_email: EmailAddress
    ) -> Success[Self, Exception] | Failure[None, Exception]:
        """
        Create a new Vendor aggregate and record a VendorCreated event.
        Returns Success(Vendor) or Failure(DomainValidationError) on validation error.
        """
        try:
            if not vendor_id:
                return Failure(
                    DomainValidationError(
                        "vendor_id is required", details=get_error_context()
                    )
                )
            if not name:
                return Failure(
                    DomainValidationError(
                        "name is required", details=get_error_context()
                    )
                )
            if not contact_email:
                return Failure(
                    DomainValidationError(
                        "contact_email is required", details=get_error_context()
                    )
                )
            vendor = cls(id=vendor_id, name=name, contact_email=contact_email)
            event = VendorCreated(
                vendor_id=vendor_id, name=name, contact_email=contact_email.value
            )
            vendor._record_event(event)
            return Success(vendor)
        except Exception as e:
            return Failure(DomainValidationError(str(e), details=get_error_context()))

    def update(
        self, name: str, contact_email: EmailAddress
    ) -> Success[None, Exception] | Failure[None, Exception]:
        """
        Update the Vendor aggregate and record a VendorUpdated event.
        Returns Success(None) or Failure(DomainValidationError) on validation error.
        """
        try:
            if not name:
                return Failure(
                    DomainValidationError(
                        "name is required", details=get_error_context()
                    )
                )
            if not contact_email:
                return Failure(
                    DomainValidationError(
                        "contact_email is required", details=get_error_context()
                    )
                )
            event = VendorUpdated(
                vendor_id=self.id, name=name, contact_email=contact_email.value
            )
            self._record_event(event)
            return Success(None)
        except Exception as e:
            return Failure(DomainValidationError(str(e), details=get_error_context()))

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

    def validate(self) -> Success[None, Exception] | Failure[None, Exception]:
        """
        Validate the aggregate's invariants. Returns Success(None) if valid, Failure(None, Exception) otherwise.
        """
        from uno.core.errors.result import Success, Failure
        from uno.core.errors.definitions import DomainValidationError
        from uno.core.errors.base import get_error_context
        from examples.app.domain.value_objects import EmailAddress

        if not self.name or not isinstance(self.name, str):
            return Failure(DomainValidationError("name must be a non-empty string", details=get_error_context()))
        if not self.contact_email or not isinstance(self.contact_email, EmailAddress):
            return Failure(DomainValidationError("contact_email must be an EmailAddress value object", details=get_error_context()))
        # Add more invariants as needed
        return Success(None)
