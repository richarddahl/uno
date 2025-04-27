"""
Integration test for TimeoutSaga: demonstrates timeouts and retries in a Uno saga.
"""
import pytest
from uno.core.events.saga_store import InMemorySagaStore
from uno.core.events.saga_manager import SagaManager
from examples.app.sagas.timeout_saga import TimeoutSaga

@pytest.mark.asyncio
async def test_timeout_saga_retries_and_timeout():
    saga_store = InMemorySagaStore()
    manager = SagaManager(saga_store)
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
    assert state.status == "failed"

    # Reset and complete
    await manager.handle_event(saga_id, "TimeoutSaga", {"type": "StepCompleted"})
    state = await saga_store.load_state(saga_id)
    assert state is None  # Saga should be cleaned up after completion
