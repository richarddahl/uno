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
from examples.app.persistence.inventory_lot_repository import InMemoryInventoryLotRepository
from examples.app.persistence.order_repository import InMemoryOrderRepository

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

def test_inventory_lot_hash_chain_and_tamper_detection(fake_lot: InventoryLot) -> None:
    from uno.core.logging import LoggerService, LoggingConfig
    repo = InMemoryInventoryLotRepository(LoggerService(LoggingConfig()))
    repo.save(fake_lot)
    assert repo.verify_integrity(fake_lot.id)
    # Tamper: replace event object with a different value (simulate tampering)
    from examples.app.domain.inventory_lot import InventoryLotCreated
    fake_lot._domain_events[0] = InventoryLotCreated(
        lot_id=fake_lot.id,
        item_id=fake_lot.item_id,
        vendor_id=fake_lot.vendor_id,
        quantity=999,  # tampered value
        purchase_price=fake_lot.purchase_price,
    )
    assert not repo.verify_integrity(fake_lot.id)

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

def test_order_hash_chain_and_tamper_detection(fake_order: Order) -> None:
    from uno.core.logging import LoggerService, LoggingConfig
    repo = InMemoryOrderRepository(LoggerService(LoggingConfig()))
    repo.save(fake_order)
    assert repo.verify_integrity(fake_order.id)
    # Tamper: replace event object with a different value (simulate tampering)
    from examples.app.domain.order import OrderCreated
    fake_order._domain_events[0] = OrderCreated(
        order_id=fake_order.id,
        item_id=fake_order.item_id,
        lot_id=fake_order.lot_id,
        vendor_id=fake_order.vendor_id,
        quantity=999,  # tampered value
        price=fake_order.price,
        order_type=fake_order.order_type,
    )
    assert not repo.verify_integrity(fake_order.id)
