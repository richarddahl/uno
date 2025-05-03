"""
Vendor domain events.

Defines all domain events related to Vendor lifecycle and state changes.
"""

from typing import ClassVar, Self

from pydantic import ConfigDict

from uno.core.domain.event import DomainEvent
from uno.core.errors.base import get_error_context
from uno.core.errors.definitions import DomainValidationError
from uno.core.errors.result import Failure, Success

from uno.domain.value_objects import EmailAddress


class VendorCreated(DomainEvent):
    """
    Event: a new vendor is created.

    Usage:
        result = VendorCreated.create(
            vendor_id="V100",
            name="Acme Distilling",
            contact_email=EmailAddress(value="info@acme.com"),
        )
        if isinstance(result, Success):
            event = result.value
        else:
            ...
    """

    vendor_id: str
    name: str
    contact_email: str
    version: ClassVar[int] = 1
    model_config = ConfigDict(frozen=True)

    @classmethod
    def create(
        cls,
        vendor_id: str,
        name: str,
        contact_email: EmailAddress,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        """
        Create a new VendorCreated event.
        Returns Success(VendorCreated) or Failure(DomainValidationError).
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
            event = cls(
                vendor_id=vendor_id,
                name=name,
                contact_email=contact_email.value,
            )
            return Success(event)
        except Exception as exc:
            return Failure(
                DomainValidationError(
                    "Failed to create VendorCreated event",
                    details={"error": str(exc)},
                )
            )

    def upcast(
        self, target_version: int
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        """
        Upcast the event to a newer version.
        """
        if target_version == self.version:
            return Success(self)
        return Failure(
            DomainValidationError(
                "Upcasting not implemented",
                details={"from": self.version, "to": target_version},
            )
        )


class VendorUpdated(DomainEvent):
    """
    Event: a vendor's information is updated.

    Usage:
        result = VendorUpdated.create(
            vendor_id="V100",
            name="Acme Spirits",
            contact_email=EmailAddress(value="hello@acme.com"),
        )
        if isinstance(result, Success):
            event = result.value
        else:
            ...
    """

    vendor_id: str
    name: str
    contact_email: str
    version: ClassVar[int] = 1
    model_config = ConfigDict(frozen=True)

    @classmethod
    def create(
        cls,
        vendor_id: str,
        name: str,
        contact_email: EmailAddress,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        """
        Create a new VendorUpdated event.
        Returns Success(VendorUpdated) or Failure(DomainValidationError).
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
            event = cls(
                vendor_id=vendor_id,
                name=name,
                contact_email=contact_email.value,
            )
            return Success(event)
        except Exception as exc:
            return Failure(
                DomainValidationError(
                    "Failed to create VendorUpdated event",
                    details={"error": str(exc)},
                )
            )

    def upcast(
        self, target_version: int
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        """
        Upcast the event to a newer version.
        """
        if target_version == self.version:
            return Success(self)
        return Failure(
            DomainValidationError(
                "Upcasting not implemented",
                details={"from": self.version, "to": target_version},
            )
        )
