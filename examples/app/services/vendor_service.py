# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Service layer for Vendor workflows in Uno.
Implements orchestration, error context propagation, and DI-ready business logic.
"""
from uno.core.errors.result import Result, Success, Failure
from uno.core.errors.definitions import DomainValidationError
from uno.core.logging import LoggerService
from examples.app.domain.vendor import Vendor
from examples.app.persistence.vendor_repository import InMemoryVendorRepository

class VendorService:
    """
    Service for Vendor workflows.
    Orchestrates domain logic, repository, and error context propagation.
    """
    def __init__(self, repo: InMemoryVendorRepository, logger: LoggerService) -> None:
        self.repo = repo
        self.logger = logger

    def create_vendor(self, vendor_id: str, name: str, contact_email: str) -> Result[Vendor, Exception]:
        # Check for existing vendor
        result = self.repo.get(vendor_id)
        if not isinstance(result, Failure):
            self.logger.warning(f"Vendor already exists: {vendor_id}")
            return Failure(DomainValidationError(f"Vendor already exists: {vendor_id}", details={"vendor_id": vendor_id}))
        # Create domain aggregate
        from examples.app.domain.value_objects import EmailAddress
        email_vo = EmailAddress(value=contact_email)
        vendor_result = Vendor.create(vendor_id=vendor_id, name=name, contact_email=email_vo)
        if isinstance(vendor_result, Failure):
            self.logger.warning(f"Failed to create Vendor: {vendor_id} ({vendor_result.error})")
            return vendor_result
        vendor = vendor_result.unwrap()
        self.repo.save(vendor)
        self.logger.info(f"Vendor created: {vendor_id}")
        return Success(vendor)

    def update_vendor(self, vendor_id: str, name: str, contact_email: str) -> Result[Vendor, Exception]:
        result = self.repo.get(vendor_id)
        if isinstance(result, Failure):
            self.logger.warning(f"Vendor not found: {vendor_id}")
            return result
        vendor = result.value
        from examples.app.domain.value_objects import EmailAddress
        email_vo = EmailAddress(value=contact_email)
        update_result = vendor.update(name, email_vo)
        if isinstance(update_result, Failure):
            self.logger.warning(f"Failed to update Vendor: {vendor_id} ({update_result.error})")
            return update_result
        self.repo.save(vendor)
        self.logger.info(f"Vendor updated: {vendor_id}")
        return Success(vendor)
