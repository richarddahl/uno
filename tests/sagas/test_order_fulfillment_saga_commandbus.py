"""
Integration test: OrderFulfillmentSaga emits commands via CommandBus as it processes events.
"""
import pytest
from uno.core.events.saga_store import InMemorySagaStore
from uno.core.events.saga_manager import SagaManager
from uno.core.events.event_bus import EventBus
from uno.core.events.command_bus import CommandBus
from examples.app.sagas.order_fulfillment_saga import OrderFulfillmentSaga

@pytest.mark.asyncio
async def test_order_fulfillment_saga_commandbus():
    saga_store = InMemorySagaStore()
    manager = SagaManager(saga_store)
    manager.register_saga(OrderFulfillmentSaga)
    bus = EventBus()
    command_bus = CommandBus()
    saga_id = "order-cmd-1"
    emitted_commands = []

    # Command handler records all commands
    async def command_handler(command):
        emitted_commands.append(command)

    command_bus.register_handler(command_handler)

    # Wire the saga manager to the bus and inject command bus into saga
    async def saga_handler(event):
        saga = manager._get_or_create_saga(saga_id, "OrderFulfillmentSaga")
        saga.set_command_bus(command_bus)
        await manager.handle_event(saga_id, "OrderFulfillmentSaga", event)

    bus.subscribe(saga_handler)

    # Publish OrderPlaced
    await bus.publish({"type": "OrderPlaced", "order_id": saga_id})
    assert emitted_commands[-1]["type"] == "ReserveInventory"
    assert emitted_commands[-1]["order_id"] == saga_id

    # Publish InventoryReserved
    await bus.publish({"type": "InventoryReserved"})
    assert emitted_commands[-1]["type"] == "ProcessPayment"
    assert emitted_commands[-1]["order_id"] == saga_id

    # Publish PaymentProcessed
    await bus.publish({"type": "PaymentProcessed"})
    # No new command should be emitted, saga completes
    state = await saga_store.load_state(saga_id)
    assert state is None
