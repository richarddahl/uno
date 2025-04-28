"""
Unit tests for Vendor <-> VendorDTO mapping functions.
"""
import pytest
from examples.app.domain.vendor import Vendor
from examples.app.domain.value_objects import EmailAddress
from examples.app.api.vendor_dtos import VendorDTO
from examples.app.api.mappers.vendor_mapper import vendor_to_dto, dto_to_vendor

def fake_vendor() -> Vendor:
    return Vendor(id="v-1", name="Acme Corp", contact_email=EmailAddress(value="acme@example.com"))

def fake_vendor_dto() -> VendorDTO:
    return VendorDTO(id="v-1", name="Acme Corp", contact_email="acme@example.com")

def test_vendor_to_dto_roundtrip():
    vendor = fake_vendor()
    dto = vendor_to_dto(vendor)
    assert isinstance(dto, VendorDTO)
    assert dto.id == vendor.id
    assert dto.name == vendor.name
    assert dto.contact_email == vendor.contact_email.value

def test_dto_to_vendor_roundtrip():
    dto = fake_vendor_dto()
    vendor = dto_to_vendor(dto)
    assert isinstance(vendor, Vendor)
    assert vendor.id == dto.id
    assert vendor.name == dto.name
    assert vendor.contact_email.value == dto.contact_email

def test_bidirectional_mapping():
    vendor = fake_vendor()
    dto = vendor_to_dto(vendor)
    vendor2 = dto_to_vendor(dto)
    assert vendor2.id == vendor.id
    assert vendor2.name == vendor.name
    assert vendor2.contact_email.value == vendor.contact_email.value
