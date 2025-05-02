"""
Unit tests for the Vendor aggregate validate() method.
"""
import pytest
from examples.app.domain.vendor.vendor import Vendor
from examples.app.domain.value_objects import EmailAddress
from uno.core.errors.result import Success, Failure

def test_vendor_validate_domain_invariants():
    # Valid case
    vendor = Vendor(id="V1", name="Acme", contact_email=EmailAddress(value="info@acme.com"))
    assert isinstance(vendor.validate(), Success)

    # Domain invariant: name must not be empty
    vendor_with_empty_name = Vendor(id="V1", name="", contact_email=EmailAddress(value="info@acme.com"))
    assert isinstance(vendor_with_empty_name.validate(), Failure)
