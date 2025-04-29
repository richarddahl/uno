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
from examples.app.persistence.vendor_repository_protocol import VendorRepository
from examples.app.services.vendor_service import VendorService

class FakeVendorRepository(VendorRepository):
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
def fake_repo() -> VendorRepository:
    return FakeVendorRepository()

@pytest.fixture
def service(fake_repo: VendorRepository, fake_logger: LoggerService) -> VendorService:
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
    # Error context details
    assert getattr(result.error, "details", None)
    assert result.error.details["vendor_id"] == "vendor-1"
    assert result.error.details["service"] == "VendorService.create_vendor"

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
    # Check error context details if present
    if isinstance(result.error, DomainValidationError):
        assert result.error.details["vendor_id"] == "vendor-404"
        assert result.error.details["service"] == "VendorService.update_vendor"
    else:
        assert "not found" in str(result.error).lower()

def test_update_vendor_invalid(service: VendorService) -> None:
    service.create_vendor("vendor-3", "Acme Corp", "info@acme.com")
    import pydantic
    try:
        service.update_vendor("vendor-3", "", "")
    except pydantic.ValidationError:
        return  # Pass: validation error raised as expected
    except Exception as exc:
        # Accept either DomainValidationError or other error, but check for context if present
        if isinstance(exc, DomainValidationError):
            assert exc.details["vendor_id"] == "vendor-3"
            assert exc.details["service"] == "VendorService.update_vendor"
        else:
            assert "invalid" in str(exc).lower()
    else:
        assert False, "Expected ValidationError or DomainValidationError for invalid input"
