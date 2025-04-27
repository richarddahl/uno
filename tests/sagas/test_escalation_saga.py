"""
Integration test for EscalationSaga: demonstrates escalation/alerting and human-in-the-loop in Uno sagas.
"""
import pytest
from uno.core.events.saga_store import InMemorySagaStore
from uno.core.events.saga_manager import SagaManager
from examples.app.sagas.escalation_saga import EscalationSaga

@pytest.mark.asyncio
async def test_escalation_saga():
    saga_store = InMemorySagaStore()
    manager = SagaManager(saga_store)
    manager.register_saga(EscalationSaga)
    saga_id = "escalate-1"

    # Fail step multiple times to trigger escalation
    await manager.handle_event(saga_id, "EscalationSaga", {"type": "StepFailed"})
    await manager.handle_event(saga_id, "EscalationSaga", {"type": "StepFailed"})
    await manager.handle_event(saga_id, "EscalationSaga", {"type": "StepFailed"})
    state = await saga_store.load_state(saga_id)
    assert state is not None
    assert state.status == "escalated"
    assert state.data["escalated"] is True

    # Simulate human approval
    await manager.handle_event(saga_id, "EscalationSaga", {"type": "EscalationApproved"})
    state = await saga_store.load_state(saga_id)
    assert state.status == "approved"
    assert state.data["approved"] is True

    # Complete the saga
    await manager.handle_event(saga_id, "EscalationSaga", {"type": "StepCompleted"})
    state = await saga_store.load_state(saga_id)
    assert state is None  # Saga should be cleaned up after completion
