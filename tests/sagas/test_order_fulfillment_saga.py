"""
Integration test for OrderFulfillmentSaga using SagaManager and InMemorySagaStore.
"""
import asyncio
import pytest
from uno.core.events.saga_store import InMemorySagaStore
from uno.core.events.saga_manager import SagaManager
from examples.app.sagas.order_fulfillment_saga import OrderFulfillmentSaga

@pytest.mark.asyncio
async def test_order_fulfillment_saga_happy_path():
    saga_store = InMemorySagaStore()
    manager = SagaManager(saga_store)
    manager.register_saga(OrderFulfillmentSaga)
    saga_id = "order-123"

    # Simulate OrderPlaced event
    await manager.handle_event(saga_id, "OrderFulfillmentSaga", {"type": "OrderPlaced", "order_id": saga_id})
    state = await saga_store.load_state(saga_id)
    assert state is not None
    assert state.status == "waiting_inventory"

    # Simulate InventoryReserved event
    await manager.handle_event(saga_id, "OrderFulfillmentSaga", {"type": "InventoryReserved"})
    state = await saga_store.load_state(saga_id)
    assert state.status == "waiting_payment"
    assert state.data["inventory_reserved"] is True

    # Simulate PaymentProcessed event
    await manager.handle_event(saga_id, "OrderFulfillmentSaga", {"type": "PaymentProcessed"})
    state = await saga_store.load_state(saga_id)
    # Saga should be completed and state deleted
    assert state is None

@pytest.mark.asyncio
async def test_order_fulfillment_saga_compensation():
    saga_store = InMemorySagaStore()
    manager = SagaManager(saga_store)
    manager.register_saga(OrderFulfillmentSaga)
    saga_id = "order-456"

    # Simulate OrderPlaced event
    await manager.handle_event(saga_id, "OrderFulfillmentSaga", {"type": "OrderPlaced", "order_id": saga_id})
    # Simulate InventoryReserved event
    await manager.handle_event(saga_id, "OrderFulfillmentSaga", {"type": "InventoryReserved"})
    # Simulate PaymentFailed event
    await manager.handle_event(saga_id, "OrderFulfillmentSaga", {"type": "PaymentFailed"})
    state = await saga_store.load_state(saga_id)
    # Saga should be completed and state deleted
    assert state is None

@pytest.mark.asyncio
async def test_order_fulfillment_saga_recovery():
    saga_store = InMemorySagaStore()
    manager = SagaManager(saga_store)
    manager.register_saga(OrderFulfillmentSaga)
    saga_id = "order-789"

    # Start saga and process first event
    await manager.handle_event(saga_id, "OrderFulfillmentSaga", {"type": "OrderPlaced", "order_id": saga_id})
    await manager.handle_event(saga_id, "OrderFulfillmentSaga", {"type": "InventoryReserved"})
    state = await saga_store.load_state(saga_id)
    assert state is not None
    assert state.status == "waiting_payment"
    assert state.data["inventory_reserved"] is True

    # Simulate a crash: re-initialize manager (store persists in memory)
    manager = SagaManager(saga_store)
    manager.register_saga(OrderFulfillmentSaga)

    # Resume saga with payment processed event
    await manager.handle_event(saga_id, "OrderFulfillmentSaga", {"type": "PaymentProcessed"})
    state = await saga_store.load_state(saga_id)
    assert state is None  # Saga completes and state is deleted
