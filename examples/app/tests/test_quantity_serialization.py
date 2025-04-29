"""
Test the serialization of Quantity value objects with CountUnit.
"""
import pytest
from examples.app.domain.value_objects import Quantity, Count, CountUnit
from uno.core.errors.utils import serialize_enums

def test_count_unit_serialization():
    """Test that CountUnit can be properly serialized to avoid JSON errors."""
    # Create a quantity with CountUnit
    quantity = Quantity.from_count(10.0)
    
    # Verify the type and value
    assert quantity.type == "count"
    assert quantity.value.value == 10.0
    assert quantity.value.unit == CountUnit.EACH
    
    # Test the serialization approach we're using in InventoryLot.create
    if quantity.type == "count":
        count_value = quantity.value.value
        # Recreate with fresh objects - this is what we do in InventoryLot.create
        event_quantity = Quantity.from_count(count_value)
        
        # Verify the new object has the same values
        assert event_quantity.type == "count"
        assert event_quantity.value.value == 10.0
        assert event_quantity.value.unit == CountUnit.EACH
        
        # Also check that serialize_enums works correctly
        serialized_data = serialize_enums(quantity.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True
        ))
        assert isinstance(serialized_data, dict)
        assert serialized_data["type"] == "count"
        assert isinstance(serialized_data["value"], dict)
        # The unit should be serialized to its name as a string
        assert serialized_data["value"]["unit"] == "EACH"
