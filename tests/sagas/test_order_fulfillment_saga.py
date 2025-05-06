"""
Integration test for OrderFulfillmentSaga using SagaManager and InMemorySagaStore.
"""

import pytest
from uno.infrastructure.di import ServiceCollection, ServiceProvider
from uno.core.events.saga_manager import SagaManager
from uno.core.events.saga_store import InMemorySagaStore
from uno.infrastructure.logging.config_service import LoggingConfigService
from uno.infrastructure.logging.logger import LoggerService, LoggingConfig
from examples.app.sagas.order_fulfillment_saga import OrderFulfillmentSaga
from typing import Any




@pytest.mark.asyncio
async def test_order_fulfillment_saga_happy_path() -> None:
    saga_store = InMemorySagaStore()
    services = ServiceCollection[Any]()
    services.add_instance(LoggingConfig, LoggingConfig())
    services.add_scoped(OrderFulfillmentSaga)
    services.add_singleton(LoggingConfigService)
    services.add_instance(LoggerService, LoggerService(LoggingConfig()))
    provider = ServiceProvider(services)
    scope = provider.create_scope()
    manager = SagaManager(saga_store, scope)
    manager.register_saga(OrderFulfillmentSaga)
    saga_id = "order-123"

    # Simulate OrderPlaced event
    await manager.handle_event(
        saga_id,
        "OrderFulfillmentSaga",
        {"type": "OrderPlaced", "order_id": saga_id},
    )
    state = await saga_store.load_state(saga_id)
    assert state is not None, "Saga state should not be None after OrderPlaced"
    assert state.status == "waiting_inventory", f"Expected status 'waiting_inventory', got {state.status}"

    # Simulate InventoryReserved event
    await manager.handle_event(
        saga_id, "OrderFulfillmentSaga", {"type": "InventoryReserved"}
    )
    state = await saga_store.load_state(saga_id)
    assert state is not None, "Saga state should not be None after InventoryReserved"
    assert state.status == "waiting_payment", f"Expected status 'waiting_payment', got {state.status}"
    assert state.data["inventory_reserved"] is True, "inventory_reserved should be True after InventoryReserved"

    # Simulate PaymentProcessed event
    await manager.handle_event(
        saga_id, "OrderFulfillmentSaga", {"type": "PaymentProcessed"}
    )
    state = await saga_store.load_state(saga_id)
    # Saga should be completed and state deleted
    assert state is None, "Saga state should be None after successful completion"


@pytest.mark.asyncio
async def test_order_fulfillment_saga_compensation() -> None:
    saga_store = InMemorySagaStore()
    services = ServiceCollection()
    services.add_scoped(OrderFulfillmentSaga)
    from uno.infrastructure.logging.config_service import LoggingConfigService

    # Register LoggingConfig as a singleton
    services.add_singleton(LoggingConfig)
    # Register LoggerService with LoggingConfig dependency
    services.add_singleton(LoggerService)
    # Register LoggingConfigService with LoggerService dependency
    services.add_singleton(LoggingConfigService)
    logger = LoggerService(LoggingConfig())
    services.add_singleton(type(logger), logger)
    provider = ServiceProvider(services)
    await provider.initialize()
    async with provider.create_scope() as scope:
        manager = SagaManager(saga_store, scope)
        manager.register_saga(OrderFulfillmentSaga)
        saga_id = "order-456"

        # Simulate OrderPlaced event
        await manager.handle_event(
            saga_id,
            "OrderFulfillmentSaga",
            {"type": "OrderPlaced", "order_id": saga_id},
        )
        # Simulate InventoryReserved event
        await manager.handle_event(
            saga_id, "OrderFulfillmentSaga", {"type": "InventoryReserved"}
        )
        # Simulate PaymentFailed event
        await manager.handle_event(
            saga_id, "OrderFulfillmentSaga", {"type": "PaymentFailed"}
        )
        state = await saga_store.load_state(saga_id)
        # Saga should be completed and state deleted
        assert state is None


@pytest.mark.asyncio
async def test_order_fulfillment_saga_recovery() -> None:
    saga_store = InMemorySagaStore()
    services = ServiceCollection()
    services.add_scoped(OrderFulfillmentSaga)
    from uno.infrastructure.logging.config_service import LoggingConfigService

    # Register LoggingConfig as a singleton
    services.add_singleton(LoggingConfig)
    # Register LoggerService with LoggingConfig dependency
    services.add_singleton(LoggerService)
    # Register LoggingConfigService with LoggerService dependency
    services.add_singleton(LoggingConfigService)
    logger = LoggerService(LoggingConfig())
    services.add_singleton(type(logger), logger)
    provider = ServiceProvider(services)
    await provider.initialize()
    async with provider.create_scope() as scope:
        manager = SagaManager(saga_store, scope)
        manager.register_saga(OrderFulfillmentSaga)
        saga_id = "order-789"

        # Start saga and process first event
        await manager.handle_event(
            saga_id,
            "OrderFulfillmentSaga",
            {"type": "OrderPlaced", "order_id": saga_id},
        )
        await manager.handle_event(
            saga_id, "OrderFulfillmentSaga", {"type": "InventoryReserved"}
        )
        state = await saga_store.load_state(saga_id)
        assert state is not None
        assert state.status == "waiting_payment"
        assert state.data["inventory_reserved"] is True

        # Simulate a crash: re-initialize manager (store persists in memory)
        manager = SagaManager(saga_store, scope)
        manager.register_saga(OrderFulfillmentSaga)

        # Resume saga with payment processed event
        await manager.handle_event(
            saga_id, "OrderFulfillmentSaga", {"type": "PaymentProcessed"}
        )
        state = await saga_store.load_state(saga_id)
        assert state is None  # Saga completes and state is deleted
