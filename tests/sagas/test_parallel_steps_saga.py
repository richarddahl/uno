"""
Integration test for ParallelStepsSaga: demonstrates fork/join orchestration in Uno sagas.
"""
import pytest
from uno.core.events.saga_store import InMemorySagaStore
from uno.core.events.saga_manager import SagaManager
from examples.app.sagas.parallel_steps_saga import ParallelStepsSaga

@pytest.mark.asyncio
async def test_parallel_steps_saga():
    saga_store = InMemorySagaStore()
    manager = SagaManager(saga_store)
    manager.register_saga(ParallelStepsSaga)
    saga_id = "parallel-1"

    # Complete step A
    await manager.handle_event(saga_id, "ParallelStepsSaga", {"type": "StepACompleted"})
    state = await saga_store.load_state(saga_id)
    assert state is not None
    assert state.data["step_a_done"] is True
    assert state.data["step_b_done"] is False
    assert state.data["joined"] is False
    assert state.status == "waiting_parallel"

    # Complete step B
    await manager.handle_event(saga_id, "ParallelStepsSaga", {"type": "StepBCompleted"})
    state = await saga_store.load_state(saga_id)
    assert state.data["step_a_done"] is True
    assert state.data["step_b_done"] is True
    assert state.data["joined"] is True
    assert state.status == "joined"

    # Finalize
    await manager.handle_event(saga_id, "ParallelStepsSaga", {"type": "Finalize"})
    state = await saga_store.load_state(saga_id)
    assert state is None  # Saga should be cleaned up after completion
