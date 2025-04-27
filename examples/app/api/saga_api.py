"""
Minimal FastAPI integration for Uno sagas: start, send events, and query status.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uno.core.events.saga_store import InMemorySagaStore
from uno.core.events.saga_manager import SagaManager
from examples.app.sagas.order_fulfillment_saga import OrderFulfillmentSaga
from examples.app.sagas.timeout_saga import TimeoutSaga
from examples.app.sagas.compensation_chain_saga import CompensationChainSaga
from examples.app.sagas.parallel_steps_saga import ParallelStepsSaga

app = FastAPI()
saga_store = InMemorySagaStore()
manager = SagaManager(saga_store)
manager.register_saga(OrderFulfillmentSaga)
manager.register_saga(TimeoutSaga)
manager.register_saga(CompensationChainSaga)
manager.register_saga(ParallelStepsSaga)

class SagaEvent(BaseModel):
    saga_type: str
    saga_id: str
    event: dict

@app.post("/saga/start")
async def start_saga(saga_type: str, saga_id: str):
    if saga_type not in manager._saga_types:
        raise HTTPException(status_code=404, detail="Unknown saga type")
    # Start the saga by sending an initial event (type must match saga)
    event = {"type": "Start", "saga_id": saga_id}
    await manager.handle_event(saga_id, saga_type, event)
    return {"message": f"Saga {saga_type} started", "saga_id": saga_id}

@app.post("/saga/event")
async def send_event(payload: SagaEvent):
    if payload.saga_type not in manager._saga_types:
        raise HTTPException(status_code=404, detail="Unknown saga type")
    await manager.handle_event(payload.saga_id, payload.saga_type, payload.event)
    return {"message": "Event processed"}

@app.get("/saga/status/{saga_id}")
async def saga_status(saga_id: str):
    # Find saga by ID (in-memory only)
    state = await saga_store.load_state(saga_id)
    if not state:
        return {"status": "not_found_or_completed"}
    return {"saga_id": saga_id, "status": state.status, "data": state.data}

@app.get("/saga/active")
async def active_sagas():
    return manager.list_active_sagas()
