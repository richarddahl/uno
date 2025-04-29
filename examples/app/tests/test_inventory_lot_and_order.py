# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Usage and integration tests for InventoryLot and Order domain models.
Covers creation, adjustment, purchase, and sale flows, with canonical serialization checks.
"""

import pytest

from examples.app.domain.inventory import InventoryItem
from examples.app.domain.inventory import InventoryLot
from examples.app.domain.order import Order
from examples.app.domain.value_objects import Count, Quantity, CountUnit
from examples.app.persistence.inventory_lot_repository import InMemoryInventoryLotRepository
from examples.app.persistence.order_repository import InMemoryOrderRepository


@pytest.fixture
def fake_item() -> InventoryItem:
    print("[DEBUG] Entering fake_item fixture")
    result = InventoryItem.create(item_id="item-1", name="Widget", quantity=100)
    print("[DEBUG] InventoryItem.create result:", result)
    assert hasattr(result, "unwrap"), f"Expected Result, got {type(result)}"
    value = result.unwrap()
    print("[DEBUG] fake_item value:", value)
    return value


@pytest.fixture
def fake_lot(fake_item: InventoryItem) -> InventoryLot:
    print("[DEBUG] Entering fake_lot fixture")
    result = InventoryLot.create(
        lot_id="lot-1",
        item_id=fake_item.id,
        quantity=Quantity.from_count(50.0),
        vendor_id="vendor-1",
        purchase_price=10.0,
    )
    print("[DEBUG] InventoryLot.create result:", result)
    assert hasattr(result, "unwrap"), f"Expected Result, got {type(result)}"
    value = result.unwrap()
    print("[DEBUG] fake_lot value:", value)
    return value


@pytest.fixture
def fake_order(fake_item: InventoryItem, fake_lot: InventoryLot) -> Order:
    print("[DEBUG] Entering fake_order fixture")
    result = Order.create(
        order_id="order-1",
        item_id=fake_item.id,
        lot_id=fake_lot.id,
        vendor_id="vendor-1",
        quantity=25.0,
        price=12.0,
        order_type="sale",
    )
    print("[DEBUG] Order.create result:", result)
    assert hasattr(result, "unwrap"), f"Expected Result, got {type(result)}"
    value = result.unwrap()
    print("[DEBUG] fake_order value:", value)
    return value


def test_inventory_lot_creation(fake_lot: InventoryLot) -> None:
    assert fake_lot.item_id == "item-1"
    assert fake_lot.vendor_id == "vendor-1"
    assert fake_lot.quantity.type == "count"
    assert fake_lot.quantity.value == Count(value=50.0, unit=CountUnit.EACH)
    assert fake_lot.purchase_price == 10.0
    # Canonical serialization
    data = fake_lot.model_dump(exclude_none=True, exclude_unset=True, by_alias=True)
    assert data["item_id"] == "item-1"
    assert data["vendor_id"] == "vendor-1"
    # Quantity is a dict with 'type' and 'value' (which is a dict for Count)
    qval = data["quantity"]
    assert qval["type"] == "count"
    # Compare using model_dump for Pydantic serialization
    assert qval["value"] == Count(value=50.0, unit=CountUnit.EACH).model_dump(
        exclude_none=True, exclude_unset=True, by_alias=True
    )
    assert data["purchase_price"] == 10.0


def test_inventory_lot_adjustment(fake_lot: InventoryLot) -> None:
    result = fake_lot.adjust_quantity(-10, reason="sold")
    assert hasattr(result, "is_success"), f"Expected Result, got {type(result)}"
    assert result.is_success, f"Expected Success, got {result}"
    lot = result.value
    assert lot.quantity.type == "count"
    assert lot.quantity.value.model_dump(
        exclude_none=True, exclude_unset=True, by_alias=True
    ) == Count(value=40.0, unit=CountUnit.EACH).model_dump(
        exclude_none=True, exclude_unset=True, by_alias=True
    )


def test_inventory_lot_hash_chain_and_tamper_detection(fake_lot: InventoryLot) -> None:
    from uno.core.logging import LoggerService, LoggingConfig

    repo = InMemoryInventoryLotRepository(LoggerService(LoggingConfig()))
    repo.save(fake_lot)
    assert repo.verify_integrity(fake_lot.id)
    # Tamper: replace event object with a different value (simulate tampering)
    from examples.app.domain.inventory import InventoryLotCreated
    from examples.app.domain.value_objects import Quantity

    fake_lot._domain_events[0] = InventoryLotCreated(
        lot_id=fake_lot.id,
        item_id=fake_lot.item_id,
        vendor_id=fake_lot.vendor_id,
        quantity=Quantity.from_count(999.0),  # tampered value
        purchase_price=fake_lot.purchase_price,
    )
    assert not repo.verify_integrity(fake_lot.id)


def test_order_creation(fake_order: Order) -> None:
    assert fake_order.item_id == "item-1"
    assert fake_order.lot_id == "lot-1"
    assert fake_order.vendor_id == "vendor-1"
    assert fake_order.quantity == 25.0
    assert fake_order.price == 12.0
    assert fake_order.order_type == "sale"
    # Canonical serialization
    data = fake_order.model_dump(exclude_none=True, exclude_unset=True, by_alias=True)
    assert data["item_id"] == "item-1"
    assert data["lot_id"] == "lot-1"
    assert data["vendor_id"] == "vendor-1"
    assert data["quantity"] == 25.0
    assert data["price"] == 12.0
    assert data["order_type"] == "sale"


def test_order_fulfillment_and_cancel(fake_order: Order) -> None:
    print("[DEBUG] fake_order before fulfill:", fake_order)
    print(
        "[DEBUG] fake_order._domain_events before fulfill:",
        getattr(fake_order, "_domain_events", []),
    )
    fake_order.fulfill(fulfilled_quantity=25)
    print("[DEBUG] fake_order after fulfill:", fake_order)
    print(
        "[DEBUG] fake_order._domain_events after fulfill:",
        getattr(fake_order, "_domain_events", []),
    )
    assert fake_order.is_fulfilled
    fake_order.cancel(reason="customer request")
    print("[DEBUG] fake_order after cancel:", fake_order)
    print(
        "[DEBUG] fake_order._domain_events after cancel:",
        getattr(fake_order, "_domain_events", []),
    )
    assert fake_order.is_cancelled


def test_order_hash_chain_and_tamper_detection(fake_order: Order) -> None:
    from uno.core.logging import LoggerService, LoggingConfig

    print("[DEBUG] fake_order before repo.save:", fake_order)
    print(
        "[DEBUG] fake_order._domain_events before repo.save:",
        getattr(fake_order, "_domain_events", []),
    )
    repo = InMemoryOrderRepository(LoggerService(LoggingConfig()))
    repo.save(fake_order)
    print("[DEBUG] fake_order after repo.save:", fake_order)
    print(
        "[DEBUG] fake_order._domain_events after repo.save:",
        getattr(fake_order, "_domain_events", []),
    )
    assert repo.verify_integrity(fake_order.id)
    # Tamper: replace event object with a different value (simulate tampering)
    from examples.app.domain.order import OrderCreated

    fake_order._domain_events[0] = OrderCreated(
        order_id=fake_order.id,
        item_id=fake_order.item_id,
        lot_id=fake_order.lot_id,
        vendor_id=fake_order.vendor_id,
        quantity=999.0,  # tampered value
        price=fake_order.price,
        order_type=fake_order.order_type,
    )
    print("[DEBUG] fake_order after tampering:", fake_order)
    print(
        "[DEBUG] fake_order._domain_events after tampering:",
        getattr(fake_order, "_domain_events", []),
    )
    assert not repo.verify_integrity(fake_order.id)
