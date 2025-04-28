"""
Integration test: OrderFulfillmentSaga reacts to events published on the EventBus.
"""
import pytest
from examples.app.sagas.order_fulfillment_saga import OrderFulfillmentSaga
from uno.core.di.container import ServiceCollection
from uno.core.di.provider import ServiceProvider
from uno.core.events.event_bus import EventBus
from uno.core.events.saga_manager import SagaManager
from uno.core.events.saga_store import InMemorySagaStore
from uno.core.logging.config_service import LoggingConfigService
from uno.core.logging.logger import LoggerService, LoggingConfig

@pytest.mark.asyncio
async def test_order_fulfillment_saga_eventbus() -> None:
    saga_store = InMemorySagaStore()
    services = ServiceCollection()
    services.add_singleton(LoggingConfig, lambda: LoggingConfig())
    services.add_scoped(LoggerService, lambda sp: LoggerService(sp.get(LoggingConfig)))
    services.add_scoped(OrderFulfillmentSaga, lambda sp: OrderFulfillmentSaga(logger=sp.get(LoggerService)))
    services.add_singleton(LoggingConfigService)
    provider = ServiceProvider(services)
    await provider.initialize()
    async with await provider.create_scope() as scope:
        manager = SagaManager(saga_store, provider)
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
