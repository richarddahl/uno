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
    assert e.to_dict() == {"value": "foo@example.com"}

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
    assert hash(e1) == hash(e2)
    assert hash(e1) != hash(e3)
