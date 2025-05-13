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
    old_email: str  # Stored as string in event
    new_email: str  # Stored as string in event
    aggregate_id: str  # Required by DomainEvent base class
    version: ClassVar[int] = 1
    model_config = ConfigDict(frozen=True, json_encoders={EmailAddress: lambda v: v.value})

    @classmethod
    def create(
        cls,
        vendor_id: str,
        old_email: str | EmailAddress,
        new_email: str | EmailAddress,
        version: int = 1,
    ) -> Self:
        """
        Create a new VendorEmailUpdated event with validation.
        
        Args:
            vendor_id: The ID of the vendor (also used as aggregate_id)
            old_email: Previous email address (string or EmailAddress)
            new_email: New email address (string or EmailAddress)
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
            if not old_email:
                raise DomainValidationError(
                    "old_email is required", details=get_error_context()
                )
            if not new_email:
                raise DomainValidationError(
                    "new_email is required", details=get_error_context()
                )
            
            # Convert EmailAddress to string if needed
            old_email_str = old_email.value if hasattr(old_email, 'value') else old_email
            new_email_str = new_email.value if hasattr(new_email, 'value') else new_email
            
            return cls(
                vendor_id=vendor_id,
                old_email=old_email_str,
                new_email=new_email_str,
                aggregate_id=vendor_id,  # Use vendor_id as aggregate_id
                version=version,
            )
        except Exception as exc:
            if isinstance(exc, DomainValidationError):
                raise
            raise DomainValidationError(
                f"Failed to create VendorEmailUpdated: {str(exc)}", details={"error": str(exc)}
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
    aggregate_id: str
    version: ClassVar[int] = 1
    model_config = ConfigDict(frozen=True, json_encoders={EmailAddress: lambda v: v.value})

    @classmethod
    def create(
        cls,
        vendor_id: str,
        name: str,
        contact_email: str | EmailAddress,
        version: int = 1,
    ) -> Self:
        """
        Create a new VendorCreated event with validation.
        
        Args:
            vendor_id: The ID of the vendor (also used as aggregate_id)
            name: The name of the vendor
            contact_email: The contact email for the vendor (string or EmailAddress)
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
            
            # Convert EmailAddress to string if needed
            email_str = contact_email.value if hasattr(contact_email, 'value') else contact_email
            
            return cls(
                vendor_id=vendor_id,
                name=name,
                contact_email=email_str,
                aggregate_id=vendor_id,  # Use vendor_id as aggregate_id
                version=version,
            )
        except Exception as exc:
            if isinstance(exc, DomainValidationError):
                raise
            raise DomainValidationError(
                f"Failed to create VendorCreated: {str(exc)}", details={"error": str(exc)}
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
    contact_email: str
    aggregate_id: str  # Required by DomainEvent base class
    version: ClassVar[int] = 1
    model_config = ConfigDict(frozen=True, json_encoders={EmailAddress: lambda v: v.value})

    @classmethod
    def create(
        cls,
        vendor_id: str,
        name: str,
        contact_email: str | EmailAddress,
        version: int = 1,
    ) -> Self:
        """
        Create a new VendorUpdated event with validation.
        
        Args:
            vendor_id: The ID of the vendor (also used as aggregate_id)
            name: The name of the vendor
            contact_email: The contact email for the vendor (string or EmailAddress)
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
            
            # Convert EmailAddress to string if needed
            email_str = contact_email.value if hasattr(contact_email, 'value') else contact_email
                
            return cls(
                vendor_id=vendor_id,
                name=name,
                contact_email=email_str,
                aggregate_id=vendor_id,  # Use vendor_id as aggregate_id
                version=version,
            )
        except Exception as exc:
            if isinstance(exc, DomainValidationError):
                raise
            raise DomainValidationError(
                f"Failed to create VendorUpdated: {str(exc)}", details={"error": str(exc)}
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
