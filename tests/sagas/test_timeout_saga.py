"""
Integration test for TimeoutSaga: demonstrates timeouts and retries in a Uno saga.
"""

import pytest

from examples.app.sagas.timeout_saga import TimeoutSaga
from uno.infrastructure.di.service_collection import ServiceCollection
from uno.infrastructure.di.service_provider import ServiceProvider
from uno.core.events.saga_manager import SagaManager
from uno.core.events.saga_store import InMemorySagaStore
from uno.infrastructure.logging.config_service import LoggingConfigService
from uno.infrastructure.logging.logger import LoggerService, LoggingConfig


@pytest.mark.asyncio
async def test_timeout_saga_retries_and_timeout() -> None:
    saga_store = InMemorySagaStore()
    services = ServiceCollection()
    services.add_singleton(LoggingConfig, lambda: LoggingConfig())
    services.add_scoped(LoggerService)
    services.add_scoped(TimeoutSaga)
    provider = ServiceProvider(services)
    await provider.initialize()
    async with provider.create_scope(scope_id="test-scope") as scope:
        manager = SagaManager(saga_store, scope)
        manager.register_saga(TimeoutSaga)
        saga_id = "timeout-1"

        # Trigger timeout event (should retry)
        await manager.handle_event(saga_id, "TimeoutSaga", {"type": "Timeout"})
        state = await saga_store.load_state(saga_id)
        assert state is not None
        assert state.status == "waiting_step"
        assert state.data["retries"] == 1
        assert state.data["timeout_triggered"] is True

        # Trigger another timeout (should retry again)
        await manager.handle_event(saga_id, "TimeoutSaga", {"type": "Timeout"})
        state = await saga_store.load_state(saga_id)
        assert state.status == "waiting_step"
        assert state.data["retries"] == 2

        # Trigger a third timeout (should fail)
        await manager.handle_event(saga_id, "TimeoutSaga", {"type": "Timeout"})
        state = await saga_store.load_state(saga_id)
        assert state is None  # State should be deleted after saga completion/failure

        # Reset and complete
        await manager.handle_event(saga_id, "TimeoutSaga", {"type": "StepCompleted"})
        state = await saga_store.load_state(saga_id)
        assert state is None  # Saga should be cleaned up after completion
