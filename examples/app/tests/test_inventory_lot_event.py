from examples.app.domain.inventory import (
    InventoryLot,
    InventoryLotAdjusted,
    InventoryLotCreated,
    InventoryLotsCombined,
    InventoryLotSplit,
)
from examples.app.domain.inventory.measurement import Measurement
from examples.app.domain.inventory.value_objects import Count, CountUnit
from uno.core.errors.definitions import DomainValidationError
from uno.core.errors.result import Failure, Success


# Test constants
TEST_LOT_ID = "lot-123"
TEST_LOT_ID_2 = "lot-abc"
TEST_AGGREGATE_ID = "item-xyz"
TEST_VENDOR_ID = "vendor-1"
TEST_PURCHASE_PRICE = 100.0
TEST_ADJUSTMENT = 10
TEST_REASON = "Stock correction"
TEST_VERSION = 1
TEST_COUNT = 10
TEST_UNIT = CountUnit.EACH
TEST_VERSION_2 = 99
TEST_ADJUSTMENT_LARGE = 20
TEST_ADJUSTMENT_SMALL = 5


def test_inventory_lot_adjusted_create_success() -> None:
    result = InventoryLotAdjusted.create(
        lot_id=TEST_LOT_ID, adjustment=TEST_ADJUSTMENT, reason=TEST_REASON
    )
    assert isinstance(result, Success)
    event = result.value
    assert event.lot_id == TEST_LOT_ID
    assert event.adjustment == TEST_ADJUSTMENT
    assert event.reason == "Stock correction"
    assert event.version == 1


def test_inventory_lot_adjusted_create_failure_missing_lot_id() -> None:
    result = InventoryLotAdjusted.create(lot_id="", adjustment=TEST_ADJUSTMENT)
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "lot_id" in result.error.details


def test_inventory_lot_adjusted_create_failure_invalid_adjustment() -> None:
    result = InventoryLotAdjusted.create(lot_id="lot-123", adjustment="bad-value")
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "adjustment" in result.error.details


def test_inventory_lot_adjusted_upcast_identity() -> None:
    result = InventoryLotAdjusted.create(lot_id="lot-123", adjustment=1)
    assert isinstance(result, Success)
    event = result.value
    upcast_result = event.upcast(event.version)
    assert isinstance(upcast_result, Success)
    assert upcast_result.value is event


def test_inventory_lot_adjusted_upcast_unimplemented() -> None:
    result = InventoryLotAdjusted.create(lot_id="lot-123", adjustment=1)
    assert isinstance(result, Success)
    event = result.value
    upcast_result = event.upcast(99)
    assert isinstance(upcast_result, Failure)
    assert isinstance(upcast_result.error, DomainValidationError)
    assert upcast_result.error.details["from"] == 1
    assert upcast_result.error.details["to"] == 99


def test_inventory_lot_created_create_success() -> None:
    # First create the lot
    lot_result = InventoryLot.create(
        lot_id=TEST_LOT_ID_2,
        aggregate_id=TEST_AGGREGATE_ID,
        measurement=TEST_COUNT,
        vendor_id=TEST_VENDOR_ID,
        purchase_price=TEST_PURCHASE_PRICE,
    )
    assert isinstance(lot_result, Success), "Expected lot creation to succeed"
    lot = lot_result.value
    assert isinstance(lot, InventoryLot), (
        "Expected lot to be an instance of InventoryLot"
    )
    assert lot.id == TEST_LOT_ID_2, "Lot ID should match input"
    assert lot.aggregate_id == TEST_AGGREGATE_ID, "Aggregate ID should match input"
    assert lot.measurement == Measurement.from_count(Count.from_each(TEST_COUNT)), (
        "Measurement should match input"
    )
    assert lot.purchase_price == TEST_PURCHASE_PRICE, (
        "Purchase price should match input"
    )
    assert len(lot._domain_events) == 1, "Expected exactly one domain event"
    event = lot._domain_events[0]
    assert isinstance(event, InventoryLotCreated), (
        "Expected event to be InventoryLotCreated"
    )
    assert event.lot_id == TEST_LOT_ID_2, "Event lot ID should match input"
    assert event.aggregate_id == TEST_AGGREGATE_ID, (
        "Event aggregate ID should match input"
    )
    assert event.measurement == Measurement.from_count(Count.from_each(TEST_COUNT)), (
        "Event measurement should match input"
    )
    assert event.vendor_id == TEST_VENDOR_ID, "Event vendor ID should match input"
    assert event.purchase_price == TEST_PURCHASE_PRICE, (
        "Event purchase price should match input"
    )
    assert event.version == TEST_VERSION
    assert event.measurement == Measurement.from_count(Count.from_each(10)), (
        "Event measurement should match input"
    )
    assert event.vendor_id == TEST_VENDOR_ID, "Event vendor ID should match input"
    assert event.purchase_price == TEST_PURCHASE_PRICE, (
        "Event purchase price should match input"
    )
    assert event.version == 1


def test_inventory_lot_created_create_failure_missing_lot_id() -> None:
    result = InventoryLotCreated.create(
        lot_id="",
        aggregate_id=TEST_AGGREGATE_ID,
        measurement=Measurement.from_count(Count.from_each(TEST_COUNT)),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "lot_id" in result.error.details


def test_inventory_lot_created_create_failure_missing_aggregate_id() -> None:
    result = InventoryLotCreated.create(
        lot_id=TEST_LOT_ID_2,
        aggregate_id="",
        measurement=Measurement.from_count(Count.from_each(TEST_COUNT)),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "aggregate_id" in result.error.details


def test_inventory_lot_created_create_failure_invalid_measurement() -> None:
    result = InventoryLotCreated.create(
        lot_id="lot-abc",
        aggregate_id="item-xyz",
        measurement="invalid-measurement",
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "measurement" in result.error.details


def test_inventory_lot_created_upcast_identity() -> None:
    # Create the event
    result = InventoryLotCreated.create(
        lot_id="lot-abc",
        aggregate_id="item-xyz",
        measurement=Measurement.from_count(Count.from_each(5)),
    )
    assert isinstance(result, Success), "Expected event creation to succeed"
    event = result.value
    assert isinstance(event, InventoryLotCreated), (
        "Expected created event to be InventoryLotCreated"
    )
    assert event.lot_id == "lot-abc", "Event lot ID should match input"
    assert event.aggregate_id == "item-xyz", "Event aggregate ID should match input"
    assert event.measurement == Measurement.from_count(Count.from_each(5)), (
        "Event measurement should match input"
    )

    # Test upcast to same version
    upcast_result = event.upcast(1)
    assert isinstance(upcast_result, Success), "Expected upcast to succeed"
    upcast_event = upcast_result.value
    assert isinstance(upcast_event, InventoryLotCreated), (
        "Expected upcast result to be InventoryLotCreated"
    )
    assert upcast_event.lot_id == event.lot_id, (
        "Upcast event lot ID should match original"
    )
    assert upcast_event.aggregate_id == event.aggregate_id, (
        "Upcast event aggregate ID should match original"
    )
    assert upcast_event.measurement == event.measurement, (
        "Upcast event measurement should match original"
    )


def test_inventory_lot_created_upcast_unimplemented() -> None:
    # Create the event
    result = InventoryLotCreated.create(
        lot_id="lot-abc",
        aggregate_id="item-xyz",
        measurement=Measurement.from_count(Count.from_each(5)),
    )
    assert isinstance(result, Success), "Expected event creation to succeed"
    event = result.value
    assert isinstance(event, InventoryLotCreated), (
        "Expected created event to be InventoryLotCreated"
    )

    # Test upcast to unsupported version
    upcast_result = event.upcast(2)
    assert isinstance(upcast_result, Failure), (
        "Expected upcast to fail for unsupported version"
    )
    assert isinstance(upcast_result.error, DomainValidationError), (
        "Expected DomainValidationError"
    )
    assert upcast_result.error.message == "Upcasting not implemented", (
        "Expected specific error message"
    )
    assert upcast_result.error.details == {"from": 1, "to": 2}, (
        "Expected specific error details"
    )


def test_inventory_lots_combined_create_success() -> None:
    result = InventoryLotsCombined.create(
        source_lot_ids=["lot-1", "lot-2"],
        source_grades=[None, None],
        source_vendor_ids=["vendor-1", "vendor-2"],
        new_lot_id="lot-3",
        aggregate_id="item-xyz",
        combined_measurement=Measurement.from_count(Count.from_each(20)),
        blended_grade=None,
        blended_vendor_ids=["vendor-1", "vendor-2"],
    )
    assert isinstance(result, Success)
    event = result.value
    assert event.source_lot_ids == ["lot-1", "lot-2"]
    assert event.new_lot_id == "lot-3"
    assert event.aggregate_id == "item-xyz"
    assert event.combined_measurement.value.value == 20
    assert event.version == 1


def test_inventory_lots_combined_create_failure_missing_source_lot_ids() -> None:
    result = InventoryLotsCombined.create(
        source_lot_ids=[],
        source_grades=[],
        source_vendor_ids=[],
        new_lot_id="lot-3",
        aggregate_id="item-xyz",
        combined_measurement=Measurement.from_count(Count.from_each(20)),
        blended_grade=None,
        blended_vendor_ids=[],
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "source_lot_ids" in result.error.details


def test_inventory_lots_combined_create_failure_missing_new_lot_id() -> None:
    result = InventoryLotsCombined.create(
        source_lot_ids=["lot-1"],
        source_grades=[None],
        source_vendor_ids=["vendor-1"],
        new_lot_id="",
        aggregate_id="item-xyz",
        combined_measurement=Measurement.from_count(Count.from_each(20)),
        blended_grade=None,
        blended_vendor_ids=["vendor-1"],
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "new_lot_id" in result.error.details


def test_inventory_lots_combined_create_failure_invalid_combined_measurement() -> None:
    result = InventoryLotsCombined.create(
        source_lot_ids=["lot-1"],
        source_grades=[None],
        source_vendor_ids=["vendor-1"],
        new_lot_id="lot-3",
        aggregate_id="item-xyz",
        combined_measurement="not-a-measurement",
        blended_grade=None,
        blended_vendor_ids=["vendor-1"],
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "combined_measurement" in result.error.details


def test_inventory_lots_combined_upcast_identity() -> None:
    result = InventoryLotsCombined.create(
        source_lot_ids=["lot-1"],
        source_grades=[None],
        source_vendor_ids=["vendor-1"],
        new_lot_id="lot-3",
        aggregate_id="item-xyz",
        combined_measurement=Measurement.from_count(Count.from_each(10)),
        blended_grade=None,
        blended_vendor_ids=["vendor-1"],
    )
    assert isinstance(result, Success)
    event = result.value
    upcast_result = event.upcast(event.version)
    assert isinstance(upcast_result, Success)
    assert upcast_result.value is event


def test_inventory_lots_combined_upcast_unimplemented() -> None:
    result = InventoryLotsCombined.create(
        source_lot_ids=["lot-1"],
        source_grades=[None],
        source_vendor_ids=["vendor-1"],
        new_lot_id="lot-3",
        aggregate_id="item-xyz",
        combined_measurement=Measurement.from_count(Count.from_each(10)),
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


def test_inventory_lot_split_create_success() -> None:
    result = InventoryLotSplit.create(
        source_lot_id="lot-1",
        new_lot_ids=["lot-2", "lot-3"],
        aggregate_id="item-xyz",
        split_quantities=[
            Measurement.from_count(Count.from_each(TEST_COUNT // 2)),
            Measurement.from_count(Count.from_each(TEST_COUNT // 2)),
        ],
    )
    assert isinstance(result, Success)
    event = result.value
    assert event.source_lot_id == "lot-1"
    assert event.new_lot_ids == ["lot-2", "lot-3"]
    assert event.aggregate_id == "item-xyz"
    assert event.split_quantities[0].value.value == 5
    assert event.version == 1


def test_inventory_lot_split_create_failure_missing_source_lot_id() -> None:
    result = InventoryLotSplit.create(
        source_lot_id="",
        new_lot_ids=["lot-2"],
        aggregate_id="item-xyz",
        split_quantities=[Measurement.from_count(Count.from_each(5))],
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "source_lot_id" in result.error.details


def test_inventory_lot_split_create_failure_missing_new_lot_ids() -> None:
    result = InventoryLotSplit.create(
        source_lot_id="lot-1",
        new_lot_ids=[],
        aggregate_id="item-xyz",
        split_quantities=[Measurement.from_count(Count.from_each(5))],
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "new_lot_ids" in result.error.details


def test_inventory_lot_split_create_failure_invalid_split_quantities() -> None:
    lot = InventoryLot(
        id="lot-1",
        aggregate_id="item-xyz",
        measurement=Measurement.from_count(Count.from_each(10)),
    )
    result = lot.split(
        split_quantities=[
            TEST_COUNT // 2,
            TEST_COUNT // 2,
            1.0,
        ],  # Invalid: total exceeds lot quantity
        new_lot_ids=["lot-2", "lot-3", "lot-4"],
    )


def test_inventory_lot_split_upcast_identity() -> None:
    result = InventoryLotSplit.create(
        source_lot_id="lot-1",
        new_lot_ids=["lot-2"],
        aggregate_id="item-xyz",
        split_quantities=[Measurement.from_count(Count.from_each(5))],
    )
    assert isinstance(result, Success)
    event = result.value
    upcast_result = event.upcast(event.version)
    assert isinstance(upcast_result, Success), "Expected upcast to succeed"
    assert upcast_result.value is event, "Expected upcast to return the same event"


def test_inventory_lot_split_upcast_unimplemented() -> None:
    result = InventoryLotSplit.create(
        source_lot_id="lot-1",
        new_lot_ids=["lot-2"],
        aggregate_id="item-xyz",
        split_quantities=[Measurement.from_count(Count.from_each(5))],
    )
    assert isinstance(result, Success)
    event = result.value
    upcast_result = event.upcast(99)
    assert isinstance(upcast_result, Failure), (
        "Expected upcast to fail for unsupported version"
    )
    assert isinstance(upcast_result.error, DomainValidationError), (
        "Expected DomainValidationError"
    )
    assert upcast_result.error.details["from"] == 1, "Expected from version to be 1"
    assert upcast_result.error.details["to"] == 99, "Expected to version to be 99"
