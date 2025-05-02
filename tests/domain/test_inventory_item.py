import pytest
from examples.app.domain.inventory import InventoryItem
from uno.core.errors.result import Failure, Success
from uno.core.errors.definitions import DomainValidationError


def test_create_success():
    result = InventoryItem.create("item-1", "Widget", 10)
    assert isinstance(result, Success)
    item = result.unwrap()
    assert item.name == "Widget"
    assert item.quantity.value.value == 10


def test_create_missing_item_id():
    result = InventoryItem.create("", "Widget", 10)
    assert isinstance(result, Failure)
    assert "item_id is required" in str(result.error)
    assert result.error is not None
    assert getattr(result.error, "details", None) is not None


def test_create_negative_quantity():
    result = InventoryItem.create("item-1", "Widget", -5)
    assert isinstance(result, Failure)
    assert "quantity must be non-negative" in str(result.error)
    assert getattr(result.error, "details", None) is not None


def test_rename_success():
    item = InventoryItem.create("item-1", "Widget", 10).unwrap()
    result = item.rename("Gadget")
    assert isinstance(result, Success)
    assert item.name == "Gadget"


def test_rename_missing_name():
    item = InventoryItem.create("item-1", "Widget", 10).unwrap()
    result = item.rename("")
    assert isinstance(result, Failure)
    assert "new_name is required" in str(result.error)
    assert getattr(result.error, "details", None) is not None


def test_adjust_quantity_success():
    item = InventoryItem.create("item-1", "Widget", 10).unwrap()
    result = item.adjust_quantity(-5)
    assert isinstance(result, Success)
    for event in item._domain_events:
        item._apply_event(event)
    assert item.quantity.value.value == 5


def test_adjust_quantity_negative():
    item = InventoryItem.create("item-1", "Widget", 2).unwrap()
    result = item.adjust_quantity(-5)
    assert isinstance(result, Failure)
    assert "resulting quantity cannot be negative" in str(result.error)
    assert getattr(result.error, "details", None) is not None


def test_unhandled_event_raises():
    item = InventoryItem.create("item-1", "Widget", 10).unwrap()

    class DummyEvent:
        pass

    with pytest.raises(DomainValidationError) as exc_info:
        item._apply_event(DummyEvent())
    assert "Unhandled event" in str(exc_info.value)
    assert getattr(exc_info.value, "context", None) is not None
