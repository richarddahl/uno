"""
Unit tests for Vendor <-> VendorDTO mapping functions.
"""
from examples.app.domain.vendor import Vendor
from examples.app.domain.value_objects import EmailAddress

def fake_vendor() -> Vendor:
    return Vendor(id="v-1", name="Acme Corp", contact_email=EmailAddress(value="acme@example.com"))


def test_vendor_model_dump_roundtrip():
    vendor = fake_vendor()
    d = vendor.model_dump()
    assert d["id"] == vendor.id
    assert d["name"] == vendor.name
    # Check EmailAddress serialization
    assert d["contact_email"] == vendor.contact_email.value

