"""
Integration test for CompensationChainSaga: demonstrates multi-step compensation in a Uno saga.
"""

import pytest

from uno.infrastructure.di.service_collection import ServiceCollection
from uno.infrastructure.di.service_provider import ServiceProvider
from uno.core.events.command_bus import CommandBus
from uno.core.events.saga_manager import SagaManager
from uno.core.events.saga_store import InMemorySagaStore
from uno.infrastructure.logging.config_service import LoggingConfigService
from uno.infrastructure.logging.logger import LoggingConfig, LoggerService
from examples.app.sagas.compensation_chain_saga import CompensationChainSaga


@pytest.mark.asyncio
async def test_compensation_chain_saga() -> None:
    saga_store = InMemorySagaStore()
    services = ServiceCollection()
    services.add_singleton(LoggingConfig, lambda: LoggingConfig())
    services.add_scoped(LoggerService)
    services.add_scoped(CompensationChainSaga)
    logger = LoggerService(LoggingConfig())
    services.add_singleton(type(logger), logger)
    provider = ServiceProvider(services)
    await provider.initialize()
    async with provider.create_scope() as scope:
        manager = SagaManager(saga_store, scope)
        manager.register_saga(CompensationChainSaga)
        saga_id = "comp-chain-1"

        # Step 1 completed
        await manager.handle_event(
            saga_id, "CompensationChainSaga", {"type": "Step1Completed"}
        )
        state = await saga_store.load_state(saga_id)
        assert state is not None
        assert state.status == "waiting_step2"
        assert state.data["step1_completed"] is True

        # Step 2 failed (should trigger compensation chain)
        await manager.handle_event(
            saga_id, "CompensationChainSaga", {"type": "Step2Failed"}
        )
        state = await saga_store.load_state(saga_id)
        assert state is None  # Saga should be cleaned up after compensation

    # To inspect compensation, re-run with compensation logging
    # (For demonstration, re-instantiate and inspect compensation_log)
    saga = CompensationChainSaga()
    saga.data["step1_completed"] = True
    saga.data["step2_completed"] = True
    await saga.compensate()
    assert saga.data["compensation_log"] == ["Compensate Step2", "Compensate Step1"]
