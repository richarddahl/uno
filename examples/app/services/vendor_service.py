# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Service layer for Vendor workflows in Uno.
Implements orchestration, error context propagation, and DI-ready business logic.
"""

from uno.errors.errors import DomainValidationError
from uno.errors.result import Failure, Result, Success
from uno.logging import LoggerService
from ..domain.vendor import Vendor
from ..persistence.vendor_repository_protocol import VendorRepository


class VendorService:
    """
    Service for Vendor workflows.
    Orchestrates domain logic, repository, and error context propagation.
    """

    def __init__(self, repo: VendorRepository, logger: LoggerService) -> None:
        self.repo = repo
        self.logger = logger

    def create_vendor(
        self, vendor_id: str, name: str, contact_email: str
    ) -> Result[Vendor, Exception]:
        """
        Create a new Vendor. Returns Success(Vendor) or Failure(DomainValidationError) with error context.
        """
        result = self.repo.get(vendor_id)
        if not isinstance(result, Failure):
            self.logger.warning(
                "Vendor already exists",
                extra={
                    "event": "vendor_exists",
                    "vendor_id": vendor_id,
                    "service": "VendorService.create_vendor",
                },
            )
            return Failure(
                DomainValidationError(
                    f"Vendor already exists: {vendor_id}",
                    details={
                        "vendor_id": vendor_id,
                        "service": "VendorService.create_vendor",
                    },
                )
            )
        # Validate email
        try:
            from examples.app.domain.vendor.value_objects import EmailAddress

            email_vo = EmailAddress(value=contact_email)
        except Exception as e:
            self.logger.warning(
                "Invalid email address for vendor creation",
                extra={
                    "event": "invalid_email",
                    "email": contact_email,
                    "error": str(e),
                    "service": "VendorService.create_vendor",
                },
            )
            return Failure(
                DomainValidationError(
                    "Invalid email address",
                    details={
                        "email": contact_email,
                        "error": str(e),
                        "service": "VendorService.create_vendor",
                    },
                )
            )
        vendor_result = Vendor.create(
            vendor_id=vendor_id, name=name, contact_email=email_vo
        )
        if isinstance(vendor_result, Failure):
            self.logger.warning(
                "Failed to create vendor",
                extra={
                    "event": "vendor_create_failed",
                    "vendor_id": vendor_id,
                    "error": str(vendor_result.error),
                    "service": "VendorService.create_vendor",
                },
            )
            err = vendor_result.error
            if isinstance(err, DomainValidationError):
                err.details = {
                    **err.details,
                    "vendor_id": vendor_id,
                    "service": "VendorService.create_vendor",
                }
            return Failure(err)
        vendor = vendor_result.unwrap()
        save_result = self.repo.save(vendor)
        if isinstance(save_result, Failure):
            self.logger.error(
                {
                    "event": "vendor_save_failed",
                    "vendor_id": vendor_id,
                    "error": str(save_result.error),
                    "service": "VendorService.create_vendor",
                }
            )
            err = save_result.error
            return Failure(err)
        self.logger.info(
            {
                "event": "vendor_created",
                "vendor_id": vendor_id,
                "service": "VendorService.create_vendor",
            }
        )
        return Success(vendor)

    def update_vendor(
        self, vendor_id: str, name: str, contact_email: str
    ) -> Result[Vendor, Exception]:
        """
        Update a Vendor. Returns Success(Vendor) or Failure(DomainValidationError) with error context.
        """
        result = self.repo.get(vendor_id)
        if isinstance(result, Failure):
            self.logger.warning(
                "Vendor not found during update",
                extra={
                    "event": "vendor_not_found",
                    "vendor_id": vendor_id,
                    "service": "VendorService.update_vendor",
                },
            )
            err = result.error
            if isinstance(err, DomainValidationError):
                err.details = {
                    **err.details,
                    "vendor_id": vendor_id,
                    "service": "VendorService.update_vendor",
                }
            return Failure(err)

        vendor = result.value

        # Validate email
        try:
            from examples.app.domain.vendor.value_objects import EmailAddress

            email_vo = EmailAddress(value=contact_email)
        except Exception as e:
            self.logger.warning(
                "Invalid email address for vendor update",
                extra={
                    "event": "invalid_email",
                    "vendor_id": vendor_id,
                    "error": str(e),
                    "service": "VendorService.update_vendor",
                },
            )
            return Failure(
                DomainValidationError(
                    "Invalid email address",
                    details={
                        "email": contact_email,
                        "error": str(e),
                        "vendor_id": vendor_id,
                        "service": "VendorService.update_vendor",
                    },
                )
            )
        # Update vendor with new values
        update_result = vendor.update(name, email_vo)
        if isinstance(update_result, Failure):
            self.logger.warning(
                "Vendor update failed",
                extra={
                    "event": "vendor_update_failed",
                    "vendor_id": vendor_id,
                    "error": str(update_result.error),
                    "service": "VendorService.update_vendor",
                },
            )
            return update_result

        # Persist updated vendor
        repo_result = self.repo.update(vendor)
        if isinstance(repo_result, Failure):
            self.logger.error(
                "Vendor repository update failed",
                extra={
                    "event": "vendor_repo_update_failed",
                    "vendor_id": vendor_id,
                    "error": str(repo_result.error),
                    "service": "VendorService.update_vendor",
                },
            )
            return Failure(repo_result.error)
        self.logger.info(
            "Vendor updated successfully",
            extra={
                "event": "vendor_updated",
                "vendor_id": vendor_id,
                "service": "VendorService.update_vendor",
            },
        )
        return repo_result
