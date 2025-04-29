# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Domain model and events for Vendor aggregate (Uno example app).

Defines the Vendor aggregate root and its domain events, supporting event sourcing and DDD best practices.
"""
from uno.core.domain.aggregate import AggregateRoot
from uno.core.domain.event import DomainEvent
from uno.core.errors.result import Success, Failure
from uno.core.errors.definitions import DomainValidationError
from uno.core.errors.base import get_error_context
from pydantic import PrivateAttr
from typing import Self
from examples.app.domain.value_objects import EmailAddress

# --- Events ---
class VendorCreated(DomainEvent):
    """
    Event: Vendor was created.

    Usage:
        result = VendorCreated.create(
            vendor_id="V100",
            name="Acme Corp",
            contact_email="info@acme.com",
        )
        if isinstance(result, Success):
            event = result.value
        else:
            # handle error context
            ...
    """
    vendor_id: str
    name: str
    contact_email: str  # Serialized as primitive for event persistence
    version: int = 1
    model_config = {"frozen": True}

    @classmethod
    def create(
        cls,
        vendor_id: str,
        name: str,
        contact_email: str,
        version: int = 1,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        try:
            if not vendor_id:
                return Failure(DomainValidationError("vendor_id is required", details=get_error_context()))
            if not name:
                return Failure(DomainValidationError("name is required", details=get_error_context()))
            if not contact_email:
                return Failure(DomainValidationError("contact_email is required", details=get_error_context()))
            event = cls(
                vendor_id=vendor_id,
                name=name,
                contact_email=contact_email,
                version=version,
            )
            return Success(event)
        except Exception as exc:
            return Failure(DomainValidationError("Failed to create VendorCreated", details={"error": str(exc)}))

    def upcast(self, target_version: int) -> Success[Self, Exception] | Failure[Self, Exception]:
        if target_version == self.version:
            return Success(self)
        return Failure(DomainValidationError("Upcasting not implemented", details={"from": self.version, "to": target_version}))

class VendorUpdated(DomainEvent):
    """
    Event: Vendor was updated.

    Usage:
        result = VendorUpdated.create(
            vendor_id="V100",
            name="Acme Corp",
            contact_email="info@acme.com",
        )
        if isinstance(result, Success):
            event = result.value
        else:
            # handle error context
            ...
    """
    vendor_id: str
    name: str
    contact_email: str  # Serialized as primitive for event persistence
    version: int = 1
    model_config = {"frozen": True}

    @classmethod
    def create(
        cls,
        vendor_id: str,
        name: str,
        contact_email: str,
        version: int = 1,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        try:
            if not vendor_id:
                return Failure(DomainValidationError("vendor_id is required", details=get_error_context()))
            if not name:
                return Failure(DomainValidationError("name is required", details=get_error_context()))
            if not contact_email:
                return Failure(DomainValidationError("contact_email is required", details=get_error_context()))
            event = cls(
                vendor_id=vendor_id,
                name=name,
                contact_email=contact_email,
                version=version,
            )
            return Success(event)
        except Exception as exc:
            return Failure(DomainValidationError("Failed to create VendorUpdated", details={"error": str(exc)}))

    def upcast(self, target_version: int) -> Success[Self, Exception] | Failure[Self, Exception]:
        if target_version == self.version:
            return Success(self)
        return Failure(DomainValidationError("Upcasting not implemented", details={"from": self.version, "to": target_version}))

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
    def create(cls, vendor_id: str, name: str, contact_email: EmailAddress) -> Success[Self, Exception] | Failure[None, Exception]:
        """
        Create a new Vendor aggregate and record a VendorCreated event.
        Returns Success(Vendor) or Failure(DomainValidationError) on validation error.
        """
        from uno.core.errors.result import Success, Failure
        from uno.core.errors.definitions import DomainValidationError
        from uno.core.errors.base import get_error_context
        try:
            if not vendor_id:
                return Failure(DomainValidationError("vendor_id is required", details=get_error_context()))
            if not name:
                return Failure(DomainValidationError("name is required", details=get_error_context()))
            if not contact_email:
                return Failure(DomainValidationError("contact_email is required", details=get_error_context()))
            vendor = cls(id=vendor_id, name=name, contact_email=contact_email)
            event = VendorCreated(vendor_id=vendor_id, name=name, contact_email=contact_email.value)
            vendor._record_event(event)
            return Success(vendor)
        except Exception as e:
            return Failure(DomainValidationError(str(e), details=get_error_context()))

    def update(self, name: str, contact_email: EmailAddress) -> Success[None, Exception] | Failure[None, Exception]:
        """
        Update the Vendor aggregate and record a VendorUpdated event.
        Returns Success(None) or Failure(DomainValidationError) on validation error.
        """
        from uno.core.errors.result import Success, Failure
        from uno.core.errors.definitions import DomainValidationError
        from uno.core.errors.base import get_error_context
        try:
            if not name:
                return Failure(DomainValidationError("name is required", details=get_error_context()))
            if not contact_email:
                return Failure(DomainValidationError("contact_email is required", details=get_error_context()))
            event = VendorUpdated(vendor_id=self.id, name=name, contact_email=contact_email.value)
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
        if isinstance(event, VendorCreated):
            self.name = event.name
            self.contact_email = EmailAddress(value=event.contact_email)
        elif isinstance(event, VendorUpdated):
            self.name = event.name
            self.contact_email = EmailAddress(value=event.contact_email)
