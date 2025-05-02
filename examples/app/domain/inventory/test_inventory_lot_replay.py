"""
Tests for InventoryLot aggregate event replay and round-trip serialization.
"""
import pytest
from examples.app.domain.inventory.lot import InventoryLot
from examples.app.domain.inventory.events import InventoryLotCreated, InventoryLotsCombined
from examples.app.domain.value_objects import Quantity, Count
from uno.core.errors.result import Success

@pytest.fixture
def lot_events():
    return [
        InventoryLotCreated(
            lot_id="L1",
            item_id="I1",
            quantity=Quantity.from_count(10),
            vendor_id="V1",
            purchase_price=100.0,
        ),
        InventoryLotsCombined(
            source_lot_ids=["L1", "L2"],
            source_grades=[None, None],
            source_vendor_ids=["V1", "V2"],
            new_lot_id="L3",
            item_id="I1",
            combined_quantity=Quantity.from_count(20),
            blended_grade=None,
            blended_vendor_ids=["V1", "V2"],
        ),
    ]

def test_inventory_lot_replay_from_events(lot_events):
    lot = InventoryLot(id="L1", item_id="", quantity=Quantity.from_count(0))
    for event in lot_events:
        lot._apply_event(event)
    assert lot.id == "L1"
    assert lot.quantity.value.value == 20
    assert isinstance(lot.quantity, Quantity)
    # Round-trip: serialize and deserialize events, replay again
    serialized = [e.model_dump() for e in lot_events]
    deserialized = [
        InventoryLotCreated.model_validate(serialized[0]),
        InventoryLotsCombined.model_validate(serialized[1]),
    ]
    lot2 = InventoryLot(id="L1", item_id="", quantity=Quantity.from_count(0))
    for event in deserialized:
        lot2._apply_event(event)
    assert lot2.quantity.value.value == lot.quantity.value.value
    assert isinstance(lot2.quantity, Quantity)
