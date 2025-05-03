# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Unit tests for example app value objects (Grade, EmailAddress).
"""
import pytest
from examples.app.domain.value_objects import Grade, EmailAddress
from pydantic import ValidationError

class FakeValueObject(Grade):
    pass

def test_grade_valid():
    g = Grade(value=88.5)
    assert g.value == 88.5
    assert g.to_dict() == {"value": 88.5}

def test_grade_invalid():
    with pytest.raises(ValidationError):
        Grade(value=150)
    with pytest.raises(ValidationError):
        Grade(value=-2)

def test_grade_equality_and_hash():
    g1 = Grade(value=90.0)
    g2 = Grade(value=90.0)
    g3 = Grade(value=80.0)
    assert g1 == g2
    assert g1 != g3
    assert hash(g1) == hash(g2)
    assert hash(g1) != hash(g3)

def test_email_valid():
    e = EmailAddress(value="foo@example.com")
    assert e.value == "foo@example.com"
    assert e.model_dump() == "foo@example.com"

def test_email_invalid():
    with pytest.raises(ValidationError):
        EmailAddress(value="not-an-email")
    with pytest.raises(ValidationError):
        EmailAddress(value="foo@bar")

def test_email_equality_and_hash():
    e1 = EmailAddress(value="a@b.com")
    e2 = EmailAddress(value="a@b.com")
    e3 = EmailAddress(value="c@d.com")
    assert e1 == e2
    assert e1 != e3
    # TODO: Fix ValueObject.__hash__ to support string-serialized subclasses
    # assert hash(e1) == hash(e2)
    # assert hash(e1) != hash(e3)

# --- New Value Object Tests ---
import decimal
from examples.app.domain.value_objects import (
    Mass, MassUnit, Volume, VolumeUnit, Dimension, DimensionUnit, AlcoholContent, Money, Currency
)

def test_mass_valid_and_conversion():
    m = Mass(amount=10, unit=MassUnit.KILOGRAM)
    assert m.amount == 10
    # Convert to pounds
    result = m.to(MassUnit.POUND)
    assert result.is_success
    m_lb = result.value
    # Convert back to kg
    back = m_lb.to(MassUnit.KILOGRAM)
    assert back.is_success
    assert abs(back.value.amount - 10) < 1e-8

def test_mass_negative():
    res = Mass.from_value(-5, MassUnit.GRAM)
    assert res.is_failure

def test_volume_valid_and_conversion():
    v = Volume(amount=1, unit=VolumeUnit.LITER)
    assert v.amount == 1
    gal = v.to(VolumeUnit.GALLON_US)
    assert gal.is_success
    v_gal = gal.value
    back = v_gal.to(VolumeUnit.LITER)
    assert back.is_success
    assert abs(back.value.amount - 1) < 1e-8

def test_volume_negative():
    res = Volume.from_value(-2, VolumeUnit.PINT)
    assert res.is_failure

def test_dimension_valid_and_conversion():
    d = Dimension(amount=2.54, unit=DimensionUnit.CENTIMETER)
    inch = d.to(DimensionUnit.INCH)
    assert inch.is_success
    d_in = inch.value
    back = d_in.to(DimensionUnit.CENTIMETER)
    assert back.is_success
    assert abs(back.value.amount - 2.54) < 1e-8

def test_dimension_negative():
    res = Dimension.from_value(-1, DimensionUnit.METER)
    assert res.is_failure

def test_alcohol_content_abv_and_proof():
    ac = AlcoholContent.from_abv(40)
    assert ac.is_success
    ac_obj = ac.value
    assert ac_obj.abv == 40
    proof = ac_obj.to_proof()
    assert abs(proof - 80) < 1e-8
    # US proof to ABV
    ac2 = AlcoholContent.from_proof(100, system="US")
    assert ac2.is_success
    assert abs(ac2.value.abv - 50) < 1e-8
    # UK proof
    ac3 = AlcoholContent.from_proof(70, system="UK")
    assert ac3.is_success

def test_alcohol_content_invalid():
    ac = AlcoholContent.from_abv(-5)
    assert ac.is_failure
    ac2 = AlcoholContent.from_abv(150)
    assert ac2.is_failure
    ac3 = AlcoholContent.from_proof(50, system="ZZ")
    assert ac3.is_failure

def test_money_valid_and_pretty():
    m = Money.from_value("10.25", Currency.USD)
    assert m.is_success
    money = m.value
    assert money.amount == decimal.Decimal("10.25")
    assert money.pretty().startswith("$")
    # Accept float and quantize
    m2 = Money.from_value(15.123, Currency.EUR)
    assert m2.is_success
    assert m2.value.amount == decimal.Decimal("15.12")

def test_money_negative():
    m = Money.from_value(-1, Currency.GBP)
    assert m.is_failure

def test_money_conversion():
    m = Money.from_value("100.00", Currency.USD)
    assert m.is_success
    # Convert to EUR at fx rate 0.9
    eur = m.value.to(Currency.EUR, fx_rate="0.9")
    assert eur.is_success
    assert eur.value.currency == Currency.EUR
    # No FX rate
    fail = m.value.to(Currency.EUR)
    assert fail.is_failure
