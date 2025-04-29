from examples.app.domain.inventory_lot import InventoryLotAdjusted, InventoryLotCreated, InventoryLotsCombined, InventoryLotSplit
from examples.app.domain.value_objects import Quantity, Count
from uno.core.errors.result import Success, Failure
from uno.core.errors.definitions import DomainValidationError


def test_inventory_lot_adjusted_create_success():
    result = InventoryLotAdjusted.create(
        lot_id="lot-123",
        adjustment=10,
        reason="Stock correction"
    )
    assert isinstance(result, Success)
    event = result.value
    assert event.lot_id == "lot-123"
    assert event.adjustment == 10
    assert event.reason == "Stock correction"
    assert event.version == 1

def test_inventory_lot_adjusted_create_failure_missing_lot_id():
    result = InventoryLotAdjusted.create(
        lot_id="",
        adjustment=5
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "lot_id" in result.error.details

def test_inventory_lot_adjusted_create_failure_invalid_adjustment():
    result = InventoryLotAdjusted.create(
        lot_id="lot-123",
        adjustment="bad-value"
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "adjustment" in result.error.details

def test_inventory_lot_adjusted_upcast_identity():
    result = InventoryLotAdjusted.create(
        lot_id="lot-123",
        adjustment=1
    )
    assert isinstance(result, Success)
    event = result.value
    upcast_result = event.upcast(event.version)
    assert isinstance(upcast_result, Success)
    assert upcast_result.value is event

def test_inventory_lot_adjusted_upcast_unimplemented():
    result = InventoryLotAdjusted.create(
        lot_id="lot-123",
        adjustment=1
    )
    assert isinstance(result, Success)
    event = result.value
    upcast_result = event.upcast(99)
    assert isinstance(upcast_result, Failure)
    assert isinstance(upcast_result.error, DomainValidationError)
    assert upcast_result.error.details["from"] == 1
    assert upcast_result.error.details["to"] == 99


def test_inventory_lot_created_create_success():
    result = InventoryLotCreated.create(
        lot_id="lot-abc",
        item_id="item-xyz",
        quantity=Quantity.from_count(Count.from_each(10)),
        vendor_id="vendor-1",
        purchase_price=100.0,
        sale_price=150.0,
    )
    assert isinstance(result, Success)
    event = result.value
    assert event.lot_id == "lot-abc"
    assert event.item_id == "item-xyz"
    assert event.quantity.value.value == 10
    assert event.vendor_id == "vendor-1"
    assert event.purchase_price == 100.0
    assert event.sale_price == 150.0
    assert event.version == 1

def test_inventory_lot_created_create_failure_missing_lot_id():
    result = InventoryLotCreated.create(
        lot_id="",
        item_id="item-xyz",
        quantity=Quantity.from_count(Count.from_each(5)),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "lot_id" in result.error.details

def test_inventory_lot_created_create_failure_missing_item_id():
    result = InventoryLotCreated.create(
        lot_id="lot-abc",
        item_id="",
        quantity=Quantity.from_count(Count.from_each(5)),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "item_id" in result.error.details

def test_inventory_lot_created_create_failure_invalid_quantity():
    result = InventoryLotCreated.create(
        lot_id="lot-abc",
        item_id="item-xyz",
        quantity="not-a-quantity",
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "quantity" in result.error.details

def test_inventory_lot_created_upcast_identity():
    result = InventoryLotCreated.create(
        lot_id="lot-abc",
        item_id="item-xyz",
        quantity=Quantity.from_count(Count.from_each(5)),
    )
    assert isinstance(result, Success)
    event = result.value
    upcast_result = event.upcast(event.version)
    assert isinstance(upcast_result, Success)
    assert upcast_result.value is event

def test_inventory_lot_created_upcast_unimplemented():
    result = InventoryLotCreated.create(
        lot_id="lot-abc",
        item_id="item-xyz",
        quantity=Quantity.from_count(Count.from_each(5)),
    )
    assert isinstance(result, Success)
    event = result.value
    upcast_result = event.upcast(99)
    assert isinstance(upcast_result, Failure)
    assert isinstance(upcast_result.error, DomainValidationError)
    assert upcast_result.error.details["from"] == 1
    assert upcast_result.error.details["to"] == 99


def test_inventory_lots_combined_create_success():
    result = InventoryLotsCombined.create(
        source_lot_ids=["lot-1", "lot-2"],
        source_grades=[None, None],
        source_vendor_ids=["vendor-1", "vendor-2"],
        new_lot_id="lot-3",
        item_id="item-xyz",
        combined_quantity=Quantity.from_count(Count.from_each(20)),
        blended_grade=None,
        blended_vendor_ids=["vendor-1", "vendor-2"],
    )
    assert isinstance(result, Success)
    event = result.value
    assert event.source_lot_ids == ["lot-1", "lot-2"]
    assert event.new_lot_id == "lot-3"
    assert event.item_id == "item-xyz"
    assert event.combined_quantity.value.value == 20
    assert event.version == 1

def test_inventory_lots_combined_create_failure_missing_source_lot_ids():
    result = InventoryLotsCombined.create(
        source_lot_ids=[],
        source_grades=[],
        source_vendor_ids=[],
        new_lot_id="lot-3",
        item_id="item-xyz",
        combined_quantity=Quantity.from_count(Count.from_each(20)),
        blended_grade=None,
        blended_vendor_ids=[],
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "source_lot_ids" in result.error.details

def test_inventory_lots_combined_create_failure_missing_new_lot_id():
    result = InventoryLotsCombined.create(
        source_lot_ids=["lot-1"],
        source_grades=[None],
        source_vendor_ids=["vendor-1"],
        new_lot_id="",
        item_id="item-xyz",
        combined_quantity=Quantity.from_count(Count.from_each(20)),
        blended_grade=None,
        blended_vendor_ids=["vendor-1"],
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "new_lot_id" in result.error.details

def test_inventory_lots_combined_create_failure_invalid_combined_quantity():
    result = InventoryLotsCombined.create(
        source_lot_ids=["lot-1"],
        source_grades=[None],
        source_vendor_ids=["vendor-1"],
        new_lot_id="lot-3",
        item_id="item-xyz",
        combined_quantity="not-a-quantity",
        blended_grade=None,
        blended_vendor_ids=["vendor-1"],
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "combined_quantity" in result.error.details

def test_inventory_lots_combined_upcast_identity():
    result = InventoryLotsCombined.create(
        source_lot_ids=["lot-1"],
        source_grades=[None],
        source_vendor_ids=["vendor-1"],
        new_lot_id="lot-3",
        item_id="item-xyz",
        combined_quantity=Quantity.from_count(Count.from_each(10)),
        blended_grade=None,
        blended_vendor_ids=["vendor-1"],
    )
    assert isinstance(result, Success)
    event = result.value
    upcast_result = event.upcast(event.version)
    assert isinstance(upcast_result, Success)
    assert upcast_result.value is event

def test_inventory_lots_combined_upcast_unimplemented():
    result = InventoryLotsCombined.create(
        source_lot_ids=["lot-1"],
        source_grades=[None],
        source_vendor_ids=["vendor-1"],
        new_lot_id="lot-3",
        item_id="item-xyz",
        combined_quantity=Quantity.from_count(Count.from_each(10)),
        blended_grade=None,
        blended_vendor_ids=["vendor-1"],
    )
    assert isinstance(result, Success)
    event = result.value
    upcast_result = event.upcast(99)
    assert isinstance(upcast_result, Failure)
    assert isinstance(upcast_result.error, DomainValidationError)
    assert upcast_result.error.details["from"] == 1
    assert upcast_result.error.details["to"] == 99

def test_inventory_lot_split_create_success():
    result = InventoryLotSplit.create(
        source_lot_id="lot-1",
        new_lot_ids=["lot-2", "lot-3"],
        item_id="item-xyz",
        split_quantities=[Quantity.from_count(Count.from_each(5)), Quantity.from_count(Count.from_each(5))],
    )
    assert isinstance(result, Success)
    event = result.value
    assert event.source_lot_id == "lot-1"
    assert event.new_lot_ids == ["lot-2", "lot-3"]
    assert event.item_id == "item-xyz"
    assert event.split_quantities[0].value.value == 5
    assert event.version == 1

def test_inventory_lot_split_create_failure_missing_source_lot_id():
    result = InventoryLotSplit.create(
        source_lot_id="",
        new_lot_ids=["lot-2"],
        item_id="item-xyz",
        split_quantities=[Quantity.from_count(Count.from_each(5))],
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "source_lot_id" in result.error.details

def test_inventory_lot_split_create_failure_missing_new_lot_ids():
    result = InventoryLotSplit.create(
        source_lot_id="lot-1",
        new_lot_ids=[],
        item_id="item-xyz",
        split_quantities=[Quantity.from_count(Count.from_each(5))],
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "new_lot_ids" in result.error.details

def test_inventory_lot_split_create_failure_invalid_split_quantities():
    result = InventoryLotSplit.create(
        source_lot_id="lot-1",
        new_lot_ids=["lot-2"],
        item_id="item-xyz",
        split_quantities=["not-a-quantity"],
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "split_quantities" in result.error.details

def test_inventory_lot_split_upcast_identity():
    result = InventoryLotSplit.create(
        source_lot_id="lot-1",
        new_lot_ids=["lot-2"],
        item_id="item-xyz",
        split_quantities=[Quantity.from_count(Count.from_each(5))],
    )
    assert isinstance(result, Success)
    event = result.value
    upcast_result = event.upcast(event.version)
    assert isinstance(upcast_result, Success)
    assert upcast_result.value is event

def test_inventory_lot_split_upcast_unimplemented():
    result = InventoryLotSplit.create(
        source_lot_id="lot-1",
        new_lot_ids=["lot-2"],
        item_id="item-xyz",
        split_quantities=[Quantity.from_count(Count.from_each(5))],
    )
    assert isinstance(result, Success)
    event = result.value
    upcast_result = event.upcast(99)
    assert isinstance(upcast_result, Failure)
    assert isinstance(upcast_result.error, DomainValidationError)
    assert upcast_result.error.details["from"] == 1
    assert upcast_result.error.details["to"] == 99
