"""
Uno Example App: Demonstrates advanced saga patterns (timeout/retry, compensation chaining) via CLI simulation.
"""
import asyncio
from uno.core.events.saga_store import InMemorySagaStore
from uno.core.events.saga_manager import SagaManager
from examples.app.sagas.timeout_saga import TimeoutSaga
from examples.app.sagas.compensation_chain_saga import CompensationChainSaga

async def demo_timeout_saga():
    print("\n--- TimeoutSaga Demo ---")
    saga_store = InMemorySagaStore()
    manager = SagaManager(saga_store)
    manager.register_saga(TimeoutSaga)
    saga_id = "timeout-demo"
    # Simulate timeouts and completion
    await manager.handle_event(saga_id, "TimeoutSaga", {"type": "Timeout"})
    await manager.handle_event(saga_id, "TimeoutSaga", {"type": "Timeout"})
    await manager.handle_event(saga_id, "TimeoutSaga", {"type": "Timeout"})
    # Should now be failed
    print("TimeoutSaga status after retries:", manager.list_active_sagas())
    # Complete
    await manager.handle_event(saga_id, "TimeoutSaga", {"type": "StepCompleted"})
    print("TimeoutSaga status after completion:", manager.list_active_sagas())

async def demo_compensation_chain_saga():
    print("\n--- CompensationChainSaga Demo ---")
    saga_store = InMemorySagaStore()
    manager = SagaManager(saga_store)
    manager.register_saga(CompensationChainSaga)
    saga_id = "comp-chain-demo"
    # Complete first step
    await manager.handle_event(saga_id, "CompensationChainSaga", {"type": "Step1Completed"})
    # Fail second step (triggers compensation)
    await manager.handle_event(saga_id, "CompensationChainSaga", {"type": "Step2Failed"})
    # Saga should be cleaned up, but we can demo compensation logic directly
    saga = CompensationChainSaga()
    saga.data["step1_completed"] = True
    saga.data["step2_completed"] = True
    await saga.compensate()
    print("Compensation log:", saga.data["compensation_log"])

if __name__ == "__main__":
    asyncio.run(demo_timeout_saga())
    asyncio.run(demo_compensation_chain_saga())
