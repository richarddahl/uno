"""
Integration test: OrderFulfillmentSaga reacts to events published on the EventBus.
"""

import pytest
from examples.app.sagas.order_fulfillment_saga import OrderFulfillmentSaga
from uno.infrastructure.di.service_collection import ServiceCollection
from uno.infrastructure.di.service_provider import ServiceProvider
from uno.infrastructure.di.service_scope import Scope
from uno.core.events.event_bus import EventBus
from uno.core.events.saga_manager import SagaManager
from uno.core.events.saga_store import InMemorySagaStore
from uno.infrastructure.logging.config_service import LoggingConfigService
from uno.infrastructure.logging.logger import LoggerService, LoggingConfig
from typing import Any, Callable, Awaitable


@pytest.mark.asyncio
async def test_order_fulfillment_saga_eventbus() -> None:
    """Test that OrderFulfillmentSaga reacts to events published on the EventBus."""
    services: ServiceCollection = ServiceCollection()  # type: ignore
    saga_store = InMemorySagaStore()
    services = ServiceCollection()  # type: ignore
    services.add_singleton(LoggingConfig, LoggingConfig)
    services.add_scoped(LoggerService, lambda: LoggerService(LoggingConfig()))
    services.add_scoped(OrderFulfillmentSaga)
    services.add_singleton(LoggingConfigService)
    services.add_singleton(EventBus)
    provider = ServiceProvider(services)
    await provider.initialize()
    async with provider.create_scope() as scope:
        manager = SagaManager(saga_store, scope)
        manager.register_saga(OrderFulfillmentSaga)
        bus = EventBus()

        saga_id = "order-evt-1"

        # Wire the saga manager to the bus: on each event, call the saga manager
        async def saga_handler(event: dict[str, Any]) -> None:
            await manager.handle_event(saga_id, "OrderFulfillmentSaga", event)

        bus.subscribe(saga_handler)

        # Publish OrderPlaced
        await bus.publish({"type": "OrderPlaced", "order_id": saga_id})
        state = await saga_store.load_state(saga_id)
        assert state is not None
        assert state.status == "waiting_inventory"  # type: ignore

        # Publish InventoryReserved
        await bus.publish({"type": "InventoryReserved", "order_id": saga_id})
        state = await saga_store.load_state(saga_id)
        assert state is not None
        assert state.status == "waiting_payment"  # type: ignore
        assert state.data["inventory_reserved"] is True

        # Publish PaymentProcessed
        await bus.publish({"type": "PaymentProcessed"})
        state = await saga_store.load_state(saga_id)
        assert state is None  # Saga should complete and state be deleted
