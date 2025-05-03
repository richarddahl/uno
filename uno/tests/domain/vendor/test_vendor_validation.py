"""
Unit tests for the Vendor aggregate validate() method.
"""

import pytest

from uno.core.errors.result import Failure, Success
from pydantic_core import ValidationError

from examples.app.domain.value_objects import EmailAddress
from examples.app.domain.vendor import Vendor


def test_vendor_validate_domain_invariants():
    # Valid case
    vendor = Vendor(
        id="V1",
        name="Acme",
        contact_email=EmailAddress(value="info@acme.com"),
    )
    assert isinstance(vendor.validate(), Success)

    # Domain invariant: name must not be empty
    vendor_with_empty_name = Vendor(
        id="V1",
        name="",
        contact_email=EmailAddress(value="info@acme.com"),
    )
    assert isinstance(vendor_with_empty_name.validate(), Failure)

    # Domain invariant: contact_email must be valid
    try:
        vendor_with_invalid_email = Vendor(
            id="V1",
            name="Acme",
            contact_email=EmailAddress(value="invalid"),  
        )
        assert isinstance(vendor_with_invalid_email.validate(), Failure)
    except ValidationError:
        pass  # Expected Pydantic validation error


def test_vendor_create_validation():
    # Valid creation
    result = Vendor.create(
        vendor_id="V1",
        name="Acme",
        contact_email=EmailAddress(value="info@acme.com"),
    )
    assert isinstance(result, Success)

    # Invalid creation: empty name
    result = Vendor.create(
        vendor_id="V1",
        name="",
        contact_email=EmailAddress(value="info@acme.com"),
    )
    assert isinstance(result, Failure)

    # Invalid creation: invalid email
    try:
        result = Vendor.create(
            vendor_id="V1",
            name="Acme",
            contact_email=EmailAddress(value="invalid"),  
        )
        assert isinstance(result, Failure)
    except ValidationError:
        pass  # Expected Pydantic validation error


def test_vendor_update_validation():
    # Create valid vendor first
    vendor = Vendor(
        id="V1",
        name="Acme",
        contact_email=EmailAddress(value="info@acme.com"),
    )

    # Valid update
    result = vendor.update(
        name="Acme Distilling",
        contact_email=EmailAddress(value="hello@acme.com"),
    )
    assert isinstance(result, Success)

    # Invalid update: empty name
    result = vendor.update(
        name="",
        contact_email=EmailAddress(value="hello@acme.com"),
    )
    assert isinstance(result, Failure)

    # Invalid update: invalid email
    try:
        result = vendor.update(
            name="Acme Distilling",
            contact_email=EmailAddress(value="invalid"),  
        )
        assert isinstance(result, Failure)
    except ValidationError:
        pass  # Expected Pydantic validation error
