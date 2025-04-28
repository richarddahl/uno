"""
Integration test for EscalationSaga: demonstrates escalation/alerting and human-in-the-loop in Uno sagas.
"""

import pytest

from uno.core.di.container import ServiceCollection
from uno.core.di.provider import ServiceProvider
from uno.core.events.saga_manager import SagaManager
from uno.core.events.saga_store import InMemorySagaStore
from uno.core.logging.config_service import LoggingConfigService
from uno.core.logging.logger import LoggingConfig, LoggerService
from examples.app.sagas.escalation_saga import EscalationSaga

@pytest.mark.asyncio
async def test_escalation_saga() -> None:
    saga_store = InMemorySagaStore()
    services = ServiceCollection()
    services.add_singleton(LoggingConfig, lambda: LoggingConfig())
    services.add_scoped(LoggerService)
    services.add_scoped(EscalationSaga)
    provider = ServiceProvider(services)
    await provider.initialize()
    async with await provider.create_scope() as scope:
        manager = SagaManager(saga_store, provider)
        manager.register_saga(EscalationSaga)
        saga_id = "escalate-1"

        # Fail step multiple times to trigger escalation
        await manager.handle_event(saga_id, "EscalationSaga", {"type": "StepFailed"})
        await manager.handle_event(saga_id, "EscalationSaga", {"type": "StepFailed"})
        await manager.handle_event(saga_id, "EscalationSaga", {"type": "StepFailed"})
        state = await saga_store.load_state(saga_id)
        assert state is not None
        assert state.status == "escalated"  # OK to check before completion
        assert state.data["escalated"] is True

        # Simulate human approval
        await manager.handle_event(saga_id, "EscalationSaga", {"type": "EscalationApproved"})
        state = await saga_store.load_state(saga_id)
        assert state is None  # State should be deleted after saga completion/approval

        # Complete the saga
        await manager.handle_event(saga_id, "EscalationSaga", {"type": "StepCompleted"})
        state = await saga_store.load_state(saga_id)
        assert state is None  # Saga should be cleaned up after completion
