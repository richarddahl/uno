"""
Test the serialization of Measurement value objects with CountUnit.
"""

from examples.app.domain.inventory.measurement import Measurement
from examples.app.domain.inventory.value_objects import CountUnit
from uno.core.errors.utils import serialize_enums


def test_count_unit_serialization() -> None:
    """Test that CountUnit can be properly serialized to avoid JSON errors."""
    # Create a measurement with CountUnit
    measurement = Measurement.from_count(10.0)

    # Verify the type and value
    assert measurement.type == "count"
    assert measurement.value.value == 10.0
    assert measurement.value.unit == CountUnit.EACH

    # Test the serialization approach we're using in InventoryLot.create
    if measurement.type == "count":
        count_value = measurement.value.value
        # Recreate with fresh objects - this is what we do in InventoryLot.create
        event_measurement = Measurement.from_count(count_value)

        # Verify the new object has the same values
        assert event_measurement.type == "count"
        assert event_measurement.value.value == 10.0
        assert event_measurement.value.unit == CountUnit.EACH

        # Also check that serialize_enums works correctly
        serialized_data = serialize_enums(
            measurement.model_dump(exclude_none=True, exclude_unset=True, by_alias=True)
        )
        assert isinstance(serialized_data, dict)
        assert serialized_data["type"] == "count"
        assert isinstance(serialized_data["value"], dict)
        # The unit should be serialized to its name as a string
        assert serialized_data["value"]["unit"] == "EACH"
