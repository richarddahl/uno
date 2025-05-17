# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""Tests for the ValueObject base class."""

import pytest
from pydantic import BaseModel, ValidationError, model_validator
from uno.domain.value_objects import ValueObject


class ExampleValueObject(ValueObject):
    """Non-final value object for testing purposes."""
    name: str
    value: int = 0
    
    @model_validator(mode='after')
    def _validate_positive(self) -> 'ExampleValueObject':
        if self.value < 0:
            raise ValueError("Value must be non-negative")
        return self


def test_value_object_creation():
    """Test basic value object creation and attribute access."""
    vo = ExampleValueObject(name="test", value=42)
    assert vo.name == "test"
    assert vo.value == 42


def test_value_object_immutability():
    """Test that value objects are immutable after creation."""
    vo = ExampleValueObject(name="test")
    with pytest.raises(ValueError, match="Instance is frozen"):
        vo.name = "new name"  # Intentional test of immutability


def test_value_object_equality():
    """Test value-based equality."""
    vo1 = ExampleValueObject(name="test", value=42)
    vo2 = ExampleValueObject(name="test", value=42)
    vo3 = ExampleValueObject(name="different", value=42)
    
    assert vo1 == vo2
    assert vo1 != vo3
    assert vo1 != "not a value object"


def test_value_object_hashing():
    """Test that value objects can be used in sets and as dictionary keys."""
    vo1 = ExampleValueObject(name="test")
    vo2 = ExampleValueObject(name="test")
    vo3 = ExampleValueObject(name="different")
    
    assert hash(vo1) == hash(vo2)
    assert hash(vo1) != hash(vo3)
    
    # Test set behavior
    s = {vo1, vo2, vo3}
    assert len(s) == 2  # vo1 and vo2 are equal
    
    # Test dict behavior
    d = {vo1: "value1", vo3: "value2"}
    assert d[vo2] == "value1"  # vo1 and vo2 are equal
    assert d[vo3] == "value2"


def test_validation():
    """Test custom validation in value objects."""
    class PositiveNumber(ExampleValueObject):
        @model_validator(mode='after')
        def _validate_positive(self) -> 'PositiveNumber':
            if self.value <= 0:
                raise ValueError("Value must be positive")
            return self
    
    # Valid case
    vo = PositiveNumber(name="test", value=42)
    assert vo.value == 42
    
    # Invalid case
    with pytest.raises(ValidationError) as exc_info:
        PositiveNumber(name="test", value=-1)
    assert "Value must be positive" in str(exc_info.value)


def test_copy_with_changes():
    """Test the copy method with changes."""
    vo1 = ExampleValueObject(name="Alice", value=30)
    vo2 = vo1.copy(value=31)
    
    assert vo1.name == "Alice"
    assert vo1.value == 30
    assert vo2.name == "Alice"
    assert vo2.value == 31
    assert vo1 != vo2


def test_serialization():
    """Test JSON serialization and deserialization."""
    vo = ExampleValueObject(name="test", value=42)
    json_str = vo.model_dump_json()
    loaded = ExampleValueObject.model_validate_json(json_str)
    
    assert vo == loaded
    assert vo is not loaded  # Should be a new instance


def test_extra_fields_not_allowed():
    """Test that extra fields are not allowed by default."""
    with pytest.raises(ValidationError) as exc_info:
        ExampleValueObject(name="test", extra_field=42)  # type: ignore[call-arg]  # Intentional test of validation
    
    assert "Extra inputs are not permitted" in str(exc_info.value)
