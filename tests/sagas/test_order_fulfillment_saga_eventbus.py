"""
Integration test: OrderFulfillmentSaga reacts to events published on the EventBus.
"""
import pytest
from uno.core.events.saga_store import InMemorySagaStore
from uno.core.events.saga_manager import SagaManager
from uno.core.events.event_bus import EventBus
from examples.app.sagas.order_fulfillment_saga import OrderFulfillmentSaga

@pytest.mark.asyncio
async def test_order_fulfillment_saga_eventbus():
    saga_store = InMemorySagaStore()
    manager = SagaManager(saga_store)
    manager.register_saga(OrderFulfillmentSaga)
    bus = EventBus()

    saga_id = "order-evt-1"

    # Wire the saga manager to the bus: on each event, call the saga manager
    async def saga_handler(event):
        await manager.handle_event(saga_id, "OrderFulfillmentSaga", event)

    bus.subscribe(saga_handler)

    # Publish OrderPlaced
    await bus.publish({"type": "OrderPlaced", "order_id": saga_id})
    state = await saga_store.load_state(saga_id)
    assert state is not None
    assert state.status == "waiting_inventory"

    # Publish InventoryReserved
    await bus.publish({"type": "InventoryReserved"})
    state = await saga_store.load_state(saga_id)
    assert state.status == "waiting_payment"
    assert state.data["inventory_reserved"] is True

    # Publish PaymentProcessed
    await bus.publish({"type": "PaymentProcessed"})
    state = await saga_store.load_state(saga_id)
    assert state is None  # Saga should complete and state be deleted
