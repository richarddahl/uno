"""
Tests for Vendor aggregate event replay and round-trip serialization.
"""
import pytest
from examples.app.domain.vendor.vendor import Vendor
from examples.app.domain.vendor.events import VendorCreated, VendorUpdated
from examples.app.domain.value_objects import EmailAddress
from uno.core.errors.result import Success

@pytest.fixture
def vendor_events():
    return [
        VendorCreated(
            vendor_id="V1",
            name="Acme",
            contact_email="info@acme.com",
        ),
        VendorUpdated(
            vendor_id="V1",
            name="Acme Inc.",
            contact_email="support@acme.com",
        ),
    ]

def test_vendor_replay_from_events(vendor_events):
    vendor = Vendor(id="V1", name="", contact_email=EmailAddress(value="replay@example.com"))
    for event in vendor_events:
        vendor._apply_event(event)
    assert vendor.id == "V1"
    assert vendor.name == "Acme Inc."
    assert isinstance(vendor.contact_email, EmailAddress)
    # Round-trip: serialize and deserialize events, replay again
    serialized = [e.model_dump() for e in vendor_events]
    deserialized = [VendorCreated(**serialized[0]), VendorUpdated(**serialized[1])]
    vendor2 = Vendor(id="V1", name="", contact_email=EmailAddress(value="replay@example.com"))
    for event in deserialized:
        vendor2._apply_event(event)
    assert vendor2.name == vendor.name
    assert isinstance(vendor2.contact_email, EmailAddress)
