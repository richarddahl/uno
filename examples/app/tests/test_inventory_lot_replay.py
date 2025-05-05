"""
Tests for InventoryLot aggregate event replay and round-trip serialization.
"""

import pytest
from examples.app.domain.inventory.lot import InventoryLot
from examples.app.domain.inventory.events import (
    InventoryLotCreated,
    InventoryLotsCombined,
)
from examples.app.domain.inventory.measurement import Measurement
from examples.app.domain.inventory.value_objects import Count
from uno.core.errors.result import Success


@pytest.fixture
def lot_events():
    return [
        InventoryLotCreated.model_construct(
            lot_id="L1",
            aggregate_id="I1",
            measurement=Measurement.from_count(10),
            vendor_id="V1",
            purchase_price=100.0,
        ),
        InventoryLotsCombined.model_construct(
            source_lot_ids=["L1", "L2"],
            source_grades=[None, None],
            source_vendor_ids=["V1", "V2"],
            new_lot_id="L3",
            aggregate_id="I1",
            combined_measurement=Measurement.from_count(20),
            blended_grade=None,
            blended_vendor_ids=["V1", "V2"],
        ),
    ]


def test_inventory_lot_replay_from_events(lot_events):
    lot = InventoryLot.model_construct(
        id="L1",
        aggregate_id="",
        measurement=Measurement.from_count(1)
    )
    for event in lot_events:
        lot._apply_event(event)
    assert lot.id == "L1"
    assert lot.measurement.value == Count.from_each(20)
    assert isinstance(lot.measurement, Measurement)
    # Round-trip: serialize and deserialize events, replay again
    # First, let's print the structure to debug
    serialized = [e.model_dump() for e in lot_events]
    
    # Need to convert the value dictionaries back to objects
    if 'measurement' in serialized[0] and isinstance(serialized[0]['measurement'], dict):
        measurement_data = serialized[0]['measurement']
        if measurement_data['type'] == 'count':
            serialized[0]['measurement'] = Measurement.from_count(measurement_data['value']['value'])
    
    if 'combined_measurement' in serialized[1] and isinstance(serialized[1]['combined_measurement'], dict):
        measurement_data = serialized[1]['combined_measurement']
        if measurement_data['type'] == 'count':
            serialized[1]['combined_measurement'] = Measurement.from_count(measurement_data['value']['value'])
    
    deserialized = [
        InventoryLotCreated.model_construct(**serialized[0]),
        InventoryLotsCombined.model_construct(**serialized[1]),
    ]
    lot2 = InventoryLot.model_construct(
        id="L1",
        aggregate_id="",
        measurement=Measurement.from_count(1)
    )
    for event in deserialized:
        lot2._apply_event(event)
    assert lot2.measurement.value == lot.measurement.value
    assert isinstance(lot2.measurement, Measurement)
