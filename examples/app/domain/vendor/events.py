"""
Vendor context domain events.
"""

from typing import ClassVar, Self

from pydantic import ConfigDict

from uno.core.domain.event import DomainEvent
from uno.core.errors.base import get_error_context
from uno.core.errors.definitions import DomainValidationError
from uno.core.errors.result import Failure, Success

from ..value_objects import EmailAddress


class VendorEmailUpdated(DomainEvent):
    """
    Event: a vendor's email address is updated.

    Usage:
        result = VendorEmailUpdated.create(
            vendor_id="V100",
            old_email=EmailAddress(value="old@example.com"),
            new_email=EmailAddress(value="new@example.com"),
        )
        if isinstance(result, Success):
            event = result.value
        else:
            ...
    """

    vendor_id: str
    old_email: EmailAddress
    new_email: EmailAddress
    version: ClassVar[int] = 1
    model_config = ConfigDict(frozen=True)

    @classmethod
    def create(
        cls,
        vendor_id: str,
        old_email: EmailAddress,
        new_email: EmailAddress,
        version: int = 1,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        try:
            if not vendor_id:
                return Failure(
                    DomainValidationError(
                        "vendor_id is required", details=get_error_context()
                    )
                )
            if not isinstance(old_email, EmailAddress):
                return Failure(
                    DomainValidationError(
                        "old_email must be an EmailAddress", details=get_error_context()
                    )
                )
            if not isinstance(new_email, EmailAddress):
                return Failure(
                    DomainValidationError(
                        "new_email must be an EmailAddress", details=get_error_context()
                    )
                )
            event = cls(
                vendor_id=vendor_id,
                old_email=old_email,
                new_email=new_email,
                version=version,
            )
            return Success(event)
        except Exception as exc:
            return Failure(
                DomainValidationError(
                    "Failed to create VendorEmailUpdated", details={"error": str(exc)}
                )
            )

    def upcast(
        self, target_version: int
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        if target_version == self.version:
            return Success(self)
        return Failure(
            DomainValidationError(
                "Upcasting not implemented",
                details={"from": self.version, "to": target_version},
            )
        )


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
    model_config = ConfigDict(frozen=True)

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
                contact_email=contact_email,
                version=version,
            )
            return Success(event)
        except Exception as exc:
            return Failure(
                DomainValidationError(
                    "Failed to create VendorCreated", details={"error": str(exc)}
                )
            )

    def upcast(
        self, target_version: int
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
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
    model_config = ConfigDict(frozen=True)

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
                contact_email=contact_email,
                version=version,
            )
            return Success(event)
        except Exception as exc:
            return Failure(
                DomainValidationError(
                    "Failed to create VendorUpdated", details={"error": str(exc)}
                )
            )

    def upcast(
        self, target_version: int
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        if target_version == self.version:
            return Success(self)
        return Failure(
            DomainValidationError(
                "Upcasting not implemented",
                details={"from": self.version, "to": target_version},
            )
        )
