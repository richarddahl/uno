# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Usage and integration tests for InventoryLot and Order domain models.
Covers creation, adjustment, purchase, and sale flows, with canonical serialization checks.
"""
import pytest
from examples.app.domain.inventory_item import InventoryItem
from examples.app.domain.inventory_lot import InventoryLot
from examples.app.domain.order import Order

@pytest.fixture
def fake_item() -> InventoryItem:
    return InventoryItem.create(item_id="item-1", name="Widget", quantity=100)

@pytest.fixture
def fake_lot(fake_item: InventoryItem) -> InventoryLot:
    return InventoryLot.create(lot_id="lot-1", item_id=fake_item.id, quantity=50, vendor_id="vendor-1", purchase_price=10.0)

@pytest.fixture
def fake_order(fake_item: InventoryItem, fake_lot: InventoryLot) -> Order:
    return Order.create(order_id="order-1", item_id=fake_item.id, lot_id=fake_lot.id, vendor_id="vendor-1", quantity=25, price=12.0, order_type="sale")

def test_inventory_lot_creation(fake_lot: InventoryLot) -> None:
    assert fake_lot.item_id == "item-1"
    assert fake_lot.vendor_id == "vendor-1"
    assert fake_lot.quantity == 50
    assert fake_lot.purchase_price == 10.0
    # Canonical serialization
    data = fake_lot.model_dump(exclude_none=True, exclude_unset=True, by_alias=True)
    assert data["item_id"] == "item-1"
    assert data["vendor_id"] == "vendor-1"
    assert data["quantity"] == 50
    assert data["purchase_price"] == 10.0

def test_inventory_lot_adjustment(fake_lot: InventoryLot) -> None:
    fake_lot.adjust_quantity(-10, reason="sold")
    assert fake_lot.quantity == 40

def test_order_creation(fake_order: Order) -> None:
    assert fake_order.item_id == "item-1"
    assert fake_order.lot_id == "lot-1"
    assert fake_order.vendor_id == "vendor-1"
    assert fake_order.quantity == 25
    assert fake_order.price == 12.0
    assert fake_order.order_type == "sale"
    # Canonical serialization
    data = fake_order.model_dump(exclude_none=True, exclude_unset=True, by_alias=True)
    assert data["item_id"] == "item-1"
    assert data["lot_id"] == "lot-1"
    assert data["vendor_id"] == "vendor-1"
    assert data["quantity"] == 25
    assert data["price"] == 12.0
    assert data["order_type"] == "sale"

def test_order_fulfillment_and_cancel(fake_order: Order) -> None:
    fake_order.fulfill(fulfilled_quantity=25)
    assert fake_order.is_fulfilled
    fake_order.cancel(reason="customer request")
    assert fake_order.is_cancelled
