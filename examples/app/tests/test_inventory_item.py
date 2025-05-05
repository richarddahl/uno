import pytest

from examples.app.domain.inventory import InventoryItem
from examples.app.domain.inventory.value_objects import CountUnit
from uno.core.errors.definitions import DomainValidationError
from uno.core.errors.result import Failure, Success


def test_create_success() -> None:
    result = InventoryItem.create("item-1", "Widget", 10)
    assert isinstance(result, Success)
    item = result.unwrap()
    assert item.name == "Widget"
    assert item.measurement.value.value == 10


def test_create_missing_aggregate_id() -> None:
    result = InventoryItem.create("", "Widget", 10)
    assert isinstance(result, Failure)
    assert "aggregate_id is required" in str(result.error)
    assert result.error is not None
    assert getattr(result.error, "details", None) is not None


def test_create_negative_measurement() -> None:
    result = InventoryItem.create("item-1", "Widget", -5)
    assert isinstance(result, Failure)
    assert "measurement must be non-negative" in str(result.error)
    assert getattr(result.error, "details", None) is not None


def test_rename_success() -> None:
    item = InventoryItem.create("item-1", "Widget", 10).unwrap()
    result = item.rename("Gadget")
    assert isinstance(result, Success)
    assert item.name == "Gadget"


def test_rename_missing_name() -> None:
    item = InventoryItem.create("item-1", "Widget", 10).unwrap()
    result = item.rename("")
    assert isinstance(result, Failure)
    assert "new_name is required" in str(result.error)
    assert getattr(result.error, "details", None) is not None


def test_adjust_measurement_success() -> None:
    item = InventoryItem.create("item-1", "Widget", 10).unwrap()
    result = item.adjust_measurement(-5)
    assert isinstance(result, Success)
    for event in item._domain_events:
        item._apply_event(event)
    assert item.measurement.value.value == 5


def test_adjust_measurement_negative() -> None:
    item = InventoryItem.create("item-1", "Widget", 2).unwrap()
    result = item.adjust_measurement(-5)
    assert isinstance(result, Failure)
    assert "resulting measurement cannot be negative" in str(result.error)
    assert getattr(result.error, "details", None) is not None


def test_unhandled_event_raises() -> None:
    # Create a Count object directly for debugging
    import logging
    import sys

    from examples.app.domain.inventory.measurement import Measurement
    from examples.app.domain.inventory.value_objects import Count

    # Set up debug logging
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    # Create with primitive value
    count = Count(value=10.0, unit=CountUnit.EACH)
    measurement = Measurement.from_count(count)
    print(f"DEBUG - Count: {count!r}")
    print(f"DEBUG - Measurement: {measurement!r}")

    # Use the factory method
    result = InventoryItem.create("item-1", "Widget", measurement)
    print(f"DEBUG - Result: {result!r}")

    if isinstance(result, Failure):
        print(f"DEBUG - Error: {result.error}")
        print(f"DEBUG - Error type: {type(result.error)}")
        print(f"DEBUG - Error details: {getattr(result.error, 'details', None)}")

    item = result.unwrap()

    class DummyEvent:
        pass

    with pytest.raises(DomainValidationError) as exc_info:
        item._apply_event(DummyEvent())
    assert "Unhandled event" in str(exc_info.value)
    assert getattr(exc_info.value, "context", None) is not None
