"""
Unit tests for value object error paths and invariants.
"""
import pytest
from examples.app.domain.value_objects import Quantity, Money, Currency, EmailAddress
from uno.core.errors.result import Success, Failure

def test_quantity_from_count_negative():
    with pytest.raises(ValueError, match="Count must be a non-negative float or int"):
        Quantity.from_count(-1)

def test_money_from_value_negative():
    result = Money.from_value(-10, Currency.USD)
    assert isinstance(result, Failure)

def test_email_address_invalid():
    # Example: EmailAddress should fail on invalid email (if implemented)
    with pytest.raises(Exception):
        EmailAddress(value="not-an-email")
