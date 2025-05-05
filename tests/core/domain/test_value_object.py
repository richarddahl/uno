# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Unit tests for uno.core.domain.value_object.ValueObject
"""

import pytest
from uno.core.domain.value_object import ValueObject
from pydantic import ValidationError


class FakeValueObject(ValueObject):
    x: int
    y: str


def test_immutability():
    vo = FakeValueObject(x=1, y="foo")
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        vo.x = 2
    with pytest.raises(ValidationError):
        vo.y = "bar"


def test_equality_and_hash():
    vo1 = FakeValueObject(x=1, y="foo")
    vo2 = FakeValueObject(x=1, y="foo")
    vo3 = FakeValueObject(x=2, y="foo")
    assert vo1 == vo2
    assert vo1 != vo3
    assert hash(vo1) == hash(vo2)
    assert hash(vo1) != hash(vo3)


def test_to_dict_and_from_dict():
    vo = FakeValueObject(x=1, y="foo")
    d = vo.to_dict()
    assert d == {"x": 1, "y": "foo"}
    result = FakeValueObject.from_dict(d)
    assert result.is_success
    vo2 = result.value
    assert vo == vo2


def test_from_dict_failure():
    # Missing required field
    result = FakeValueObject.from_dict({"x": 1})
    assert result.is_failure
    assert isinstance(result.error, Exception)


def test_invalid_extra_fields():
    with pytest.raises(ValidationError):
        FakeValueObject(x=1, y="foo", z=123)


def test_none_and_unset_fields():
    class OptionalVO(ValueObject):
        a: int | None = None
        b: str | None = None

    vo = OptionalVO()
    d = vo.to_dict()
    assert "a" not in d and "b" not in d
    result = OptionalVO.from_dict({})
    assert result.is_success
    vo2 = result.value
    assert vo == vo2
