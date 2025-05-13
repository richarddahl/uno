# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Service layer for Vendor workflows in Uno.
Implements orchestration, error context propagation, and DI-ready business logic.
"""

from uno.domain.errors import DomainValidationError
from uno.errors.base import get_error_context
from uno.logging import LoggerProtocol
from ..domain.vendor import Vendor
from ..persistence.vendor_repository_protocol import VendorRepository


class VendorService:
    """
    Service for Vendor workflows.
    Orchestrates domain logic, repository, and error context propagation.
    """

    def __init__(self, repo: VendorRepository, logger: LoggerProtocol) -> None:
        self.repo = repo
        self.logger = logger

    def create_vendor(self, vendor_id: str, name: str, contact_email: str) -> Vendor:
        """
        Create a new Vendor.

        Args:
            vendor_id: The ID for the new vendor
            name: The vendor name
            contact_email: The vendor contact email

        Returns:
            The created Vendor

        Raises:
            DomainValidationError: If validation fails
        """
        # Check if vendor already exists
        result = self.repo.get(vendor_id)
        if result is not None:
            await self.logger.warning(
                "Vendor already exists",
                extra={
                    "event": "vendor_exists",
                    "vendor_id": vendor_id,
                    "service": "VendorService.create_vendor",
                },
            )
            raise DomainValidationError(
                f"Vendor already exists: {vendor_id}",
                details={
                    "vendor_id": vendor_id,
                    "service": "VendorService.create_vendor",
                },
            )

        # Validate email
        try:
            from examples.app.domain.vendor.value_objects import EmailAddress

            email_vo = EmailAddress(value=contact_email)
        except Exception as e:
            await self.logger.warning(
                "Invalid email address for vendor creation",
                extra={
                    "event": "invalid_email",
                    "email": contact_email,
                    "error": str(e),
                    "service": "VendorService.create_vendor",
                },
            )
            raise DomainValidationError(
                "Invalid email address",
                details={
                    "email": contact_email,
                    "error": str(e),
                    "service": "VendorService.create_vendor",
                },
            ) from e

        # Create the vendor
        vendor = Vendor.create(vendor_id=vendor_id, name=name, contact_email=email_vo)

        # Save the vendor
        self.repo.save(vendor)

        await self.logger.info(
            {
                "event": "vendor_created",
                "vendor_id": vendor_id,
                "service": "VendorService.create_vendor",
            }
        )
        return vendor

    def update_vendor(self, vendor_id: str, name: str, contact_email: str) -> Vendor:
        """
        Update a Vendor.

        Args:
            vendor_id: The ID of the vendor to update
            name: The new vendor name
            contact_email: The new vendor contact email

        Returns:
            The updated Vendor

        Raises:
            DomainValidationError: If validation fails
        """
        # Get the vendor
        result = self.repo.get(vendor_id)
        if result is None:
            await self.logger.warning(
                "Vendor not found during update",
                extra={
                    "event": "vendor_not_found",
                    "vendor_id": vendor_id,
                    "service": "VendorService.update_vendor",
                },
            )
            raise DomainValidationError(
                f"Vendor not found: {vendor_id}",
                details={
                    "vendor_id": vendor_id,
                    "service": "VendorService.update_vendor",
                },
            )

        vendor = result

        # Validate email
        try:
            from examples.app.domain.vendor.value_objects import EmailAddress

            email_vo = EmailAddress(value=contact_email)
        except Exception as e:
            await self.logger.warning(
                "Invalid email address for vendor update",
                extra={
                    "event": "invalid_email",
                    "vendor_id": vendor_id,
                    "error": str(e),
                    "service": "VendorService.update_vendor",
                },
            )
            raise DomainValidationError(
                "Invalid email address",
                details={
                    "email": contact_email,
                    "error": str(e),
                    "vendor_id": vendor_id,
                    "service": "VendorService.update_vendor",
                },
            ) from e

        # Update vendor with new values
        vendor.update(name, email_vo)

        # Persist updated vendor
        self.repo.update(vendor)

        await self.logger.info(
            "Vendor updated successfully",
            extra={
                "event": "vendor_updated",
                "vendor_id": vendor_id,
                "service": "VendorService.update_vendor",
            },
        )
        return vendor
