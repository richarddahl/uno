# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Value objects tests using pytest.
"""

from decimal import Decimal
from enum import Enum
from typing import Any, Literal, Self, TypeVar

import pytest
from pydantic import ConfigDict, Field, ValidationError
from uno.core.errors.result import Failure, Success

from examples.app.domain.inventory.measurement import Measurement
from examples.app.domain.inventory.value_objects import (
    AlcoholContent,
    Currency,
    Dimension,
    DimensionUnit,
    Grade,
    Mass,
    MassUnit,
    Money,
    Volume,
    VolumeUnit,
)
from examples.app.domain.vendor.value_objects import EmailAddress

# Unit testing constants
FLOAT_TOLERANCE = 1e-8
VALID_ABV = 40.0
VALID_AMOUNT = 10.0
VALID_MASS = 10.0
VALID_VOLUME = 1.5
VALID_DIMENSION = 2.54
VALID_MONEY = 10.25
VALID_MONEY_AMOUNT = 15.129
VALID_MONEY_QUANTIZED = 15.13
VALID_FX_RATE = 0.9


def test_email_valid() -> None:
    """Test valid email address creation."""
    email = EmailAddress(value="test@example.com")
    assert email is not None, "Expected email to be created successfully"
    assert str(email) == "test@example.com", (
        "Email string representation should match input"
    )


def test_email_invalid() -> None:
    """Test that invalid email addresses raise validation errors."""
    # Direct construction will raise ValidationError
    with pytest.raises(ValidationError):
        EmailAddress(value="not_an_email")


def test_grade_valid() -> None:
    """Test valid grade creation."""
    grade = Grade(value=85.5)
    assert grade.value == 85.5, "Grade value should match input"
    assert str(grade) == "85.5", "Grade string representation should match value"


def test_grade_comparison() -> None:
    """Test grade comparison operators."""
    grade1 = Grade(value=80)
    grade2 = Grade(value=90)
    grade3 = Grade(value=80)

    assert grade1 < grade2, "Grade 80 should be less than grade 90"
    assert grade1 <= grade2, "Grade 80 should be less than or equal to grade 90"
    assert grade1 <= grade3, "Grade 80 should be equal to grade 80"
    assert grade1 == grade3, "Grade 80 should be equal to grade 80"
    assert grade1 >= grade3, "Grade 80 should be greater than or equal to grade 80"


def test_grade_invalid() -> None:
    """Test that invalid grades raise validation errors."""
    with pytest.raises(ValidationError):
        Grade(value=101)  # Over max

    with pytest.raises(ValidationError):
        Grade(value=-1)  # Under min


def test_mass_valid() -> None:
    """Test valid mass creation."""
    # Create a Mass instance with unit in g
    m = Mass(type="mass", value=10.0, unit=MassUnit.GRAM)
    assert m.value == 10.0, "Mass value should match input"
    assert m.unit == MassUnit.GRAM, "Mass unit should be grams"

    # String representation
    assert str(m) == "10.0 g", "Mass string representation should match value and unit"

    # Convert to Measurement
    measurement = m.to_measurement()
    assert measurement.type == "mass", "Measurement type should be mass"
    assert measurement.value.value == 10.0, "Measurement value should match input"


def test_mass_invalid() -> None:
    """Test that negative mass values are rejected."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="must be >= 0.0"):
        Mass(type="mass", value=-5.0, unit=MassUnit.GRAM)


def test_volume_valid() -> None:
    """Test valid volume creation."""
    # Create a Volume instance
    v = Volume(type="volume", value=VALID_VOLUME, unit=VolumeUnit.MILLILITER)
    assert v.value == VALID_VOLUME
    assert v.unit == VolumeUnit.MILLILITER

    # String representation
    assert str(v) == "1.5 mL"


def test_volume_invalid() -> None:
    """Test that negative volume values are rejected."""
    # Volume doesn't have a pydantic validator for negative values,
    # but we could implement one similar to Money validation
    # This test is a placeholder for future validation
    pass


def test_dimension_valid() -> None:
    """Test valid dimension creation."""
    # Create a Dimension instance
    d = Dimension(
        type="dimension", value=VALID_DIMENSION, unit=DimensionUnit.MILLIMETER
    )
    assert d.value == VALID_DIMENSION
    assert d.unit == DimensionUnit.MILLIMETER

    # String representation
    assert str(d) == "2.54 mm"


def test_dimension_invalid() -> None:
    """Test that negative dimension values are rejected."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="Dimension must be >="):
        Dimension(type="dimension", value=-1.0, unit=DimensionUnit.MILLIMETER)


def test_alcohol_content_valid() -> None:
    """Test valid alcohol content creation."""
    # Direct construction using percentage
    ac = AlcoholContent(percentage=Decimal(VALID_ABV))
    assert ac.percentage == VALID_ABV

    # String representation
    assert str(ac) == f"{VALID_ABV}% ABV"

    # Serialization
    data = ac.model_dump()
    assert data == {"percentage": VALID_ABV}


def test_alcohol_content_invalid() -> None:
    """Test invalid alcohol content validation."""
    # Test under minimum
    with pytest.raises(ValidationError):
        AlcoholContent(percentage=Decimal(-5.0))

    # Test over maximum
    with pytest.raises(ValidationError):
        AlcoholContent(percentage=Decimal(150.0))


def test_money_valid() -> None:
    """Test valid money creation and formatting."""
    # Direct construction with decimal string
    money = Money(amount=Decimal(str(VALID_MONEY)), currency=Currency.USD)
    assert money.amount == Decimal(str(VALID_MONEY))
    assert money.currency == Currency.USD

    # String representation includes currency symbol
    assert money.pretty().startswith("$")

    # Serialization
    data = money.to_dict()
    assert data == {"amount": float(VALID_MONEY), "currency": "USD"}

    # Test automatic quantization with float
    money = Money(amount=Decimal(str(VALID_MONEY_AMOUNT)), currency=Currency.EUR)
    # Should quantize to 2 decimal places
    assert money.amount == Decimal(str(VALID_MONEY_QUANTIZED))


def test_money_negative() -> None:
    """Test validation of negative money values."""
    # Validate that negative amounts are rejected
    with pytest.raises(ValidationError):
        Money(amount=-1, currency=Currency.GBP)


def test_money_conversion() -> None:
    """Test currency conversion with and without fx rates."""
    # Create base money object
    money = Money(amount=Decimal("100.00"), currency=Currency.USD)

    # Convert to EUR at fx rate 0.9
    result = money.to(Currency.EUR, fx_rate=Decimal("0.9"))
    assert isinstance(result, Success)
    eur_money = result.value
    assert eur_money.currency == Currency.EUR
    assert eur_money.amount == Decimal("90.00"), (
        "Converted amount should match expected value"
    )

    # Conversion without FX rate should fail
    result = money.to(Currency.EUR)
    assert isinstance(result, Failure)


def test_measurement_from_count_negative() -> None:
    with pytest.raises(ValidationError, match="Count value must be non-negative"):
        Measurement.from_count(-1)


def test_money_from_value_negative() -> None:
    result = Money.from_value(-10, Currency.USD)
    assert isinstance(result, Failure)


def test_email_address_invalid() -> None:
    # Example: EmailAddress should fail on invalid email (if implemented)
    with pytest.raises(Exception):
        EmailAddress(value="not-an-email")
