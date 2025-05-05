"""
Unit tests for the Vendor aggregate validate() method.
"""

import pytest
from pydantic_core import ValidationError

from examples.app.domain.vendor import Vendor
from examples.app.domain.vendor.value_objects import EmailAddress
from uno.core.errors.result import Failure, Success


def test_vendor_validate_domain_invariants() -> None:
    # Valid case
    vendor = Vendor(
        id="V1",
        name="Acme",
        contact_email=EmailAddress(value="info@acme.com"),
    )
    assert vendor.name == "Acme"

    with pytest.raises(ValidationError) as excinfo:
        Vendor(
            id="V1",
            name="",
            contact_email=EmailAddress(value="info@acme.com"),
        )
    assert "name must be a non-empty string" in str(excinfo.value)

    with pytest.raises(ValidationError):
        Vendor(
            id="V1",
            name="Acme",
            contact_email=EmailAddress(value="invalid"),
        )


def test_vendor_create_validation() -> None:
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


def test_vendor_update_validation() -> None:
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
