# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Unit tests for VendorService (Uno example app).
Covers all Result-based success and error paths, including validation and error context propagation.
"""
import pytest
from uno.core.errors.result import Success, Failure
from uno.core.errors.definitions import DomainValidationError
from uno.core.logging import LoggerService, LoggingConfig
from examples.app.domain.vendor import Vendor
from examples.app.services.vendor_service import VendorService

class FakeVendorRepository:
    def __init__(self):
        self._vendors = {}
    def get(self, vendor_id: str):
        vendor = self._vendors.get(vendor_id)
        if vendor:
            return Success(vendor)
        return Failure(Exception("not found"))
    def save(self, vendor: Vendor):
        self._vendors[vendor.id] = vendor
        return Success(vendor)

@pytest.fixture
def fake_logger() -> LoggerService:
    return LoggerService(LoggingConfig())

@pytest.fixture
def fake_repo() -> FakeVendorRepository:
    return FakeVendorRepository()

@pytest.fixture
def service(fake_repo: FakeVendorRepository, fake_logger: LoggerService) -> VendorService:
    return VendorService(fake_repo, fake_logger)

def test_create_vendor_success(service: VendorService) -> None:
    result = service.create_vendor("vendor-1", "Acme Corp", "info@acme.com")
    assert isinstance(result, Success)
    vendor = result.value
    assert vendor.id == "vendor-1"
    assert vendor.name == "Acme Corp"
    assert vendor.contact_email.value == "info@acme.com"

def test_create_vendor_duplicate(service: VendorService) -> None:
    service.create_vendor("vendor-1", "Acme Corp", "info@acme.com")
    result = service.create_vendor("vendor-1", "Acme Corp", "info@acme.com")
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "already exists" in str(result.error)

import pydantic

def test_create_vendor_invalid(service: VendorService) -> None:
    with pytest.raises(pydantic.ValidationError):
        service.create_vendor("", "", "")

def test_update_vendor_success(service: VendorService) -> None:
    service.create_vendor("vendor-2", "Acme Corp", "info@acme.com")
    result = service.update_vendor("vendor-2", "Acme Distilling", "contact@acme.com")
    assert isinstance(result, Success)
    vendor = result.value
    assert vendor.name == "Acme Distilling"
    assert vendor.contact_email.value == "contact@acme.com"

def test_update_vendor_not_found(service: VendorService) -> None:
    result = service.update_vendor("vendor-404", "Name", "email@example.com")
    assert isinstance(result, Failure)
    assert "not found" in str(result.error).lower()

def test_update_vendor_invalid(service: VendorService) -> None:
    service.create_vendor("vendor-3", "Acme Corp", "info@acme.com")
    import pydantic
    with pytest.raises(pydantic.ValidationError):
        service.update_vendor("vendor-3", "", "")
