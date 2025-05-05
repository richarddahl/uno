"""
Tests for Order aggregate event replay and round-trip serialization.
"""

import pytest

from examples.app.domain.inventory.measurement import Measurement
from examples.app.domain.inventory.value_objects import (
    Currency,
    Money,
    Count,
    CountUnit,
)
from examples.app.domain.order.events import OrderCreated, OrderFulfilled
from examples.app.domain.order.order import Order


@pytest.fixture
def order_events():
    return [
        OrderCreated(
            order_id="O1",
            aggregate_id="I1",
            lot_id="L1",
            vendor_id="V1",
            measurement=Measurement.from_count(Count(value=10, unit=CountUnit.EACH)),
            price=Money.from_value(100, Currency.USD).unwrap(),
            order_type="purchase",
        ),
        OrderFulfilled(order_id="O1", fulfilled_measurement=10),
    ]


def test_order_replay_from_events(order_events):
    order = Order.replay_from_events("O1", order_events)
    assert order.id == "O1"
    assert order.is_fulfilled is True
    assert isinstance(order.measurement, Measurement)
    assert isinstance(order.price, Money)
    # Round-trip: serialize and deserialize events, replay again
    serialized = [e.model_dump() for e in order_events]
    deserialized = [
        OrderCreated.model_validate(serialized[0]),
        OrderFulfilled.model_validate(serialized[1]),
    ]
    order2 = Order.replay_from_events("O1", deserialized)
    assert order2.id == order.id
    assert order2.is_fulfilled == order.is_fulfilled
    assert isinstance(order2.measurement, Measurement)
    assert isinstance(order2.price, Money)
