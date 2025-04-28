"""
Integration test for OrderFulfillmentSaga using SagaManager and InMemorySagaStore.
"""
import pytest
from uno.core.di import ServiceCollection, ServiceProvider
from uno.core.events.saga_manager import SagaManager
from uno.core.events.saga_store import InMemorySagaStore
from uno.core.logging.config_service import LoggingConfigService
from uno.core.logging.logger import LoggerService, LoggingConfig
from examples.app.sagas.order_fulfillment_saga import OrderFulfillmentSaga

@pytest.mark.asyncio
async def test_order_fulfillment_saga_happy_path():
    saga_store = InMemorySagaStore()
    services = ServiceCollection()
    # Register saga and all logger dependencies for DI
    services.add_singleton(LoggingConfig, lambda: LoggingConfig())
    services.add_scoped(LoggerService, lambda sp: LoggerService(sp.get(LoggingConfig)))
    services.add_scoped(OrderFulfillmentSaga, lambda sp: OrderFulfillmentSaga(logger=sp.get(LoggerService)))
    services.add_singleton(LoggingConfigService)
    provider = ServiceProvider(services)
    await provider.initialize()
    async with await provider.create_scope() as scope:
        manager = SagaManager(saga_store, provider)
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
    services = ServiceCollection()
    services.add_scoped(OrderFulfillmentSaga, lambda sp: OrderFulfillmentSaga(logger=sp.get(LoggerService)))
    from uno.core.logging.logger import LoggerService, LoggingConfig
    from uno.core.logging.config_service import LoggingConfigService
    # Register LoggingConfig as a singleton
    services.add_singleton(LoggingConfig)
    # Register LoggerService with LoggingConfig dependency
    services.add_singleton(LoggerService)
    # Register LoggingConfigService with LoggerService dependency
    services.add_singleton(LoggingConfigService)
    provider = ServiceProvider(services)
    await provider.initialize()
    async with await provider.create_scope() as scope:
        manager = SagaManager(saga_store, provider)
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
    services = ServiceCollection()
    services.add_scoped(OrderFulfillmentSaga, lambda sp: OrderFulfillmentSaga(logger=sp.get(LoggerService)))
    from uno.core.logging.logger import LoggerService, LoggingConfig
    from uno.core.logging.config_service import LoggingConfigService
    # Register LoggingConfig as a singleton
    services.add_singleton(LoggingConfig)
    # Register LoggerService with LoggingConfig dependency
    services.add_singleton(LoggerService)
    # Register LoggingConfigService with LoggerService dependency
    services.add_singleton(LoggingConfigService)
    provider = ServiceProvider(services)
    await provider.initialize()
    async with await provider.create_scope() as scope:
        manager = SagaManager(saga_store, provider)
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
        manager = SagaManager(saga_store, provider)
        manager.register_saga(OrderFulfillmentSaga)

        # Resume saga with payment processed event
        await manager.handle_event(saga_id, "OrderFulfillmentSaga", {"type": "PaymentProcessed"})
        state = await saga_store.load_state(saga_id)
        assert state is None  # Saga completes and state is deleted
