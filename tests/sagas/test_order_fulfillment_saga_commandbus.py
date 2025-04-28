"""
Integration test: OrderFulfillmentSaga emits commands via CommandBus as it processes events.
"""
import pytest
from uno.core.events.command_bus import CommandBus
from uno.core.di.container import ServiceCollection
from uno.core.di.provider import ServiceProvider
from uno.core.events.event_bus import EventBus
from uno.core.events.saga_manager import SagaManager
from uno.core.events.saga_store import InMemorySagaStore
from uno.core.logging.config_service import LoggingConfigService
from uno.core.logging.logger import LoggerService, LoggingConfig
from examples.app.sagas.order_fulfillment_saga import OrderFulfillmentSaga

@pytest.mark.asyncio
async def test_order_fulfillment_saga_commandbus() -> None:
    saga_store = InMemorySagaStore()
    saga_id = "order-cmd-1"
    emitted_commands = []

    # Command handler records all commands
    async def command_handler(command):
        emitted_commands.append(command)

    # DI setup
    services = ServiceCollection()
    services.add_singleton(LoggingConfig, lambda: LoggingConfig())
    services.add_scoped(LoggerService)
    services.add_scoped(OrderFulfillmentSaga)
    services.add_singleton(LoggingConfigService)
    command_bus = CommandBus()
    services.add_instance(CommandBus, command_bus)
    logger = LoggerService(LoggingConfig())
    provider = ServiceProvider(logger, services)
    await provider.initialize()
    async with await provider.create_scope() as scope:
        manager = SagaManager(saga_store, provider)
        manager.register_saga(OrderFulfillmentSaga)
        # Inject the CommandBus into the saga instance
        saga_result = scope.get_service(OrderFulfillmentSaga)
        saga_instance = saga_result.value
        saga_instance.set_command_bus(command_bus)
        bus = EventBus()
        command_bus.register_handler(command_handler)

        # Wire the saga manager to the bus
        async def saga_handler(event):
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
