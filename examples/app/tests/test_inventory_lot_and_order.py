# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Usage and integration tests for InventoryLot and Order domain models.
Covers creation, adjustment, purchase, and sale flows, with canonical serialization checks.
"""

import pytest

from examples.app.domain.inventory import InventoryItem, InventoryLot
from examples.app.domain.inventory.measurement import Measurement
from examples.app.domain.inventory.value_objects import Count, CountUnit
from examples.app.domain.order import Order
from examples.app.persistence.inventory_lot_repository import (
    InMemoryInventoryLotRepository,
)
from examples.app.persistence.order_repository import InMemoryOrderRepository


@pytest.fixture
def fake_item() -> InventoryItem:
    result = InventoryItem.create(aggregate_id="item-1", name="Widget", measurement=100)
    assert hasattr(result, "unwrap"), f"Expected Result, got {type(result)}"
    value = result.unwrap()
    return value


@pytest.fixture
def fake_lot(fake_item: InventoryItem) -> InventoryLot:
    result = InventoryLot.create(
        lot_id="lot-1",
        aggregate_id=fake_item.id,
        measurement=Measurement.from_count(50.0),
        vendor_id="vendor-1",
        purchase_price=10.0,
    )
    assert hasattr(result, "unwrap"), f"Expected Result, got {type(result)}"
    value = result.unwrap()
    return value


@pytest.fixture
def fake_order(fake_item: InventoryItem, fake_lot: InventoryLot) -> Order:
    from examples.app.domain.inventory.measurement import Measurement
    from examples.app.domain.inventory.value_objects import Currency, Money

    result = Order.create(
        order_id="order-1",
        aggregate_id=fake_item.id,
        lot_id=fake_lot.id,
        vendor_id="vendor-1",
        measurement=Measurement.from_count(25.0),
        price=Money.from_value(12.0, currency=Currency.USD).unwrap(),
        order_type="sale",
    )
    assert hasattr(result, "unwrap"), f"Expected Result, got {type(result)}"
    value = result.unwrap()
    return value


def test_inventory_lot_creation(fake_lot: InventoryLot) -> None:
    assert fake_lot.aggregate_id == "item-1"
    assert fake_lot.vendor_id == "vendor-1"
    assert fake_lot.measurement.type == "count"
    assert fake_lot.measurement.value.value == 50.0
    assert fake_lot.measurement.value.unit == CountUnit.EACH
    assert fake_lot.purchase_price == 10.0
    # Canonical serialization
    data = fake_lot.model_dump(exclude_none=True, exclude_unset=True, by_alias=True)
    assert data["aggregate_id"] == "item-1"
    assert data["vendor_id"] == "vendor-1"
    # Measurement is a dict with 'type' and 'value' (which is a dict for Count)
    qval = data["measurement"]
    assert qval["type"] == "count"
    assert qval["value"] == {'type': 'count', 'value': 50.0, 'unit': CountUnit.EACH}
    assert data["purchase_price"] == 10.0


def test_inventory_lot_adjustment(fake_lot: InventoryLot) -> None:
    result = fake_lot.adjust_measurement(-10, reason="sold")
    assert hasattr(result, "is_success"), f"Expected Result, got {type(result)}"
    assert result.is_success, f"Expected Success, got {result}"
    lot = result.value
    assert lot.measurement.type == "count"
    assert lot.measurement.value.value == 40.0
    assert lot.measurement.value.unit == CountUnit.EACH


def test_inventory_lot_hash_chain_and_tamper_detection(fake_lot: InventoryLot) -> None:
    from uno.infrastructure.logging import LoggerService, LoggingConfig

    repo = InMemoryInventoryLotRepository(LoggerService(LoggingConfig()))
    repo.save(fake_lot)
    assert repo.verify_integrity(fake_lot.id)
    # Tamper: replace event object with a different value (simulate tampering)
    from examples.app.domain.inventory import InventoryLotCreated
    from examples.app.domain.inventory.measurement import Measurement

    fake_lot._domain_events[0] = InventoryLotCreated.model_construct(
        lot_id=fake_lot.id,
        aggregate_id=fake_lot.aggregate_id,
        vendor_id=fake_lot.vendor_id,
        measurement=Measurement.from_count(999.0),  # tampered value
        purchase_price=fake_lot.purchase_price,
    )
    assert not repo.verify_integrity(fake_lot.id)


def test_order_creation(fake_order: Order) -> None:
    from examples.app.domain.inventory.measurement import Measurement
    from examples.app.domain.inventory.value_objects import Money

    assert fake_order.aggregate_id == "item-1"
    assert fake_order.lot_id == "lot-1"
    assert fake_order.vendor_id == "vendor-1"
    assert isinstance(fake_order.measurement, Measurement)
    assert fake_order.measurement.value.value == 25.0  # Compare the float inside Count
    assert isinstance(fake_order.price, Money)
    assert float(fake_order.price.amount) == 12.0
    assert fake_order.order_type == "sale"
    # Canonical serialization
    data = fake_order.model_dump(exclude_none=True, exclude_unset=True, by_alias=True)
    assert data["aggregate_id"] == "item-1"
    assert data["lot_id"] == "lot-1"
    assert data["vendor_id"] == "vendor-1"
    assert data["measurement"]["value"]["value"] == 25.0
    assert data["measurement"]["value"]["unit"] == CountUnit.EACH
    assert float(data["price"]["amount"]) == 12.0
    assert data["order_type"] == "sale"


def test_order_replay_restores_value_objects(fake_order: Order) -> None:
    # Simulate event replay for a new Order instance
    from examples.app.domain.inventory.measurement import Measurement
    from examples.app.domain.inventory.value_objects import Currency, Money
    from examples.app.domain.order import Order, OrderCreated

    events = [
        OrderCreated(
            order_id=fake_order.id,
            aggregate_id=fake_order.aggregate_id,
            lot_id=fake_order.lot_id,
            vendor_id=fake_order.vendor_id,
            measurement=Measurement.from_count(25.0),
            price=Money.from_value(12.0, currency=Currency.USD).unwrap(),
            order_type="sale",
        )
    ]
    replayed = Order.replay_from_events(fake_order.id, events)
    assert isinstance(replayed.measurement, Measurement)
    assert replayed.measurement.value.value == 25.0  # Compare the float inside Count
    assert isinstance(replayed.price, Money)
    assert float(replayed.price.amount) == 12.0
    assert replayed.order_type == "sale"


def test_order_fulfillment_and_cancel(fake_order: Order) -> None:
    fake_order.fulfill(fulfilled_measurement=25)
    assert fake_order.is_fulfilled
    fake_order.cancel(reason="customer request")
    assert fake_order.is_cancelled


def test_order_hash_chain_and_tamper_detection(fake_order: Order) -> None:
    from uno.infrastructure.logging import LoggerService, LoggingConfig

    repo = InMemoryOrderRepository(LoggerService(LoggingConfig()))
    repo.save(fake_order)
    assert repo.verify_integrity(fake_order.id)
    # Tamper: replace event object with a different value (simulate tampering)
    # Tamper with the underlying event log on the aggregate itself
    # This simulates a real-world tamper and should break the hash chain
    tampered_order = repo._orders[fake_order.id]
    events = list(getattr(tampered_order, "_domain_events", []))
    first_event = events[0]
    tampered_event = first_event.model_copy(
        update={"measurement": Measurement.from_count(999.0)}
    )
    events[0] = tampered_event
    setattr(tampered_order, "_domain_events", events)
    assert not repo.verify_integrity(fake_order.id)  # Should now fail
