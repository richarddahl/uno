"""
Vendor context domain events.
"""

from typing import ClassVar, Self

from pydantic import ConfigDict

from examples.app.domain.vendor.value_objects import EmailAddress
from uno.errors.base import get_error_context
from uno.domain.errors import DomainValidationError
from uno.events import DomainEvent


class VendorEmailUpdated(DomainEvent):
    """
    Event: a vendor's email address is updated.

    Usage:
        try:
            event = VendorEmailUpdated.create(
                vendor_id="V100",
                old_email=EmailAddress(value="old@example.com"),
                new_email=EmailAddress(value="new@example.com"),
            )
            # use event
        except DomainValidationError as e:
            # handle error
            ...
    """

    vendor_id: str
    old_email: EmailAddress
    new_email: EmailAddress
    version: int = 1
    model_config = ConfigDict(frozen=True)

    @classmethod
    def create(
        cls,
        vendor_id: str,
        old_email: EmailAddress,
        new_email: EmailAddress,
        version: int = 1,
    ) -> Self:
        """
        Create a new VendorEmailUpdated event with validation.
        
        Args:
            vendor_id: The ID of the vendor
            old_email: Previous email address
            new_email: New email address
            version: Event version
            
        Returns:
            A new VendorEmailUpdated event
            
        Raises:
            DomainValidationError: If validation fails
        """
        try:
            if not vendor_id:
                raise DomainValidationError(
                    "vendor_id is required", details=get_error_context()
                )
            if not isinstance(old_email, EmailAddress):
                raise DomainValidationError(
                    "old_email must be an EmailAddress", details=get_error_context()
                )
            if not isinstance(new_email, EmailAddress):
                raise DomainValidationError(
                    "new_email must be an EmailAddress", details=get_error_context()
                )
            
            return cls(
                vendor_id=vendor_id,
                old_email=old_email,
                new_email=new_email,
                version=version,
            )
        except Exception as exc:
            if isinstance(exc, DomainValidationError):
                raise
            raise DomainValidationError(
                "Failed to create VendorEmailUpdated", details={"error": str(exc)}
            ) from exc

    def upcast(self, target_version: int) -> Self:
        """
        Upcast to a newer version of the event.
        
        Args:
            target_version: The version to upcast to
            
        Returns:
            The upcasted event
            
        Raises:
            DomainValidationError: If upcasting is not implemented for the target version
        """
        if target_version == self.version:
            return self
            
        raise DomainValidationError(
            "Upcasting not implemented",
            details={"from": self.version, "to": target_version},
        )


# --- Events ---
class VendorCreated(DomainEvent):
    """
    Event: Vendor was created.

    Usage:
        try:
            event = VendorCreated.create(
                vendor_id="V100",
                name="Acme Corp",
                contact_email="info@acme.com",
            )
            # use event
        except DomainValidationError as e:
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
    ) -> Self:
        """
        Create a new VendorCreated event with validation.
        
        Args:
            vendor_id: The ID of the vendor
            name: The name of the vendor
            contact_email: The contact email for the vendor
            version: Event version
            
        Returns:
            A new VendorCreated event
            
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
                
            return cls(
                vendor_id=vendor_id,
                name=name,
                contact_email=contact_email,
                version=version,
            )
        except Exception as exc:
            if isinstance(exc, DomainValidationError):
                raise
            raise DomainValidationError(
                "Failed to create VendorCreated", details={"error": str(exc)}
            ) from exc

    def upcast(self, target_version: int) -> Self:
        """
        Upcast to a newer version of the event.
        
        Args:
            target_version: The version to upcast to
            
        Returns:
            The upcasted event
            
        Raises:
            DomainValidationError: If upcasting is not implemented for the target version
        """
        if target_version == self.version:
            return self
            
        raise DomainValidationError(
            "Upcasting not implemented",
            details={"from": self.version, "to": target_version},
        )


class VendorUpdated(DomainEvent):
    """
    Event: Vendor was updated.

    Usage:
        try:
            event = VendorUpdated.create(
                vendor_id="V100",
                name="Acme Corp",
                contact_email="info@acme.com",
            )
            # use event
        except DomainValidationError as e:
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
    ) -> Self:
        """
        Create a new VendorUpdated event with validation.
        
        Args:
            vendor_id: The ID of the vendor
            name: The name of the vendor
            contact_email: The contact email for the vendor
            version: Event version
            
        Returns:
            A new VendorUpdated event
            
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
                
            return cls(
                vendor_id=vendor_id,
                name=name,
                contact_email=contact_email,
                version=version,
            )
        except Exception as exc:
            if isinstance(exc, DomainValidationError):
                raise
            raise DomainValidationError(
                "Failed to create VendorUpdated", details={"error": str(exc)}
            ) from exc

    def upcast(self, target_version: int) -> Self:
        """
        Upcast to a newer version of the event.
        
        Args:
            target_version: The version to upcast to
            
        Returns:
            The upcasted event
            
        Raises:
            DomainValidationError: If upcasting is not implemented for the target version
        """
        if target_version == self.version:
            return self
            
        raise DomainValidationError(
            "Upcasting not implemented",
            details={"from": self.version, "to": target_version},
        )
