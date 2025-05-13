"""
Minimal FastAPI integration for Uno sagas: start, send events, and query status.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uno.config import config
from uno.sagas import SagaManager
from uno.sagas.implementations.memory import InMemorySagaStore
from uno.persistence.event_sourcing.implementations.postgres.saga_store import (
    PostgresSagaStore,
)
from uno.persistence.event_sourcing.implementations.memory.bus import InMemoryEventBus
from uno.commands.implementations.memory_bus import InMemoryCommandBus
from uno.persistence.event_sourcing.implementations.postgres.bus import (
    PostgresEventBus,
    PostgresCommandBus,
)
from examples.app.sagas.order_fulfillment_saga import OrderFulfillmentSaga
from examples.app.sagas.timeout_saga import TimeoutSaga
from examples.app.sagas.compensation_chain_saga import CompensationChainSaga
from examples.app.sagas.parallel_steps_saga import ParallelStepsSaga
from examples.app.sagas.escalation_saga import EscalationSaga
import asyncio

app = FastAPI()

# --- Config-driven backend selection ---
BUS_BACKEND = config.get("BUS_BACKEND", "memory")
PG_DSN = config.get("UNO_PG_DSN", "")

if BUS_BACKEND == "postgres":
    saga_store = PostgresSagaStore(PG_DSN)
    event_bus = PostgresEventBus(PG_DSN)
    command_bus = PostgresCommandBus(PG_DSN)

    # Ensure async connections on startup
    async def _startup():
        await saga_store.connect()
        await event_bus.connect()
        await command_bus.connect()

    asyncio.get_event_loop().run_until_complete(_startup())
else:
    saga_store = InMemorySagaStore()
    event_bus = InMemoryEventBus()
    command_bus = InMemoryCommandBus()

manager = SagaManager(saga_store, event_bus=event_bus, command_bus=command_bus)

from uno.logging import LoggerProtocol, LoggingConfig

logger = LoggerProtocol(LoggingConfig())


# --- Pydantic models ---
class StartSagaRequest(BaseModel):
    saga_type: str
    input: dict


class StartSagaResponse(BaseModel):
    saga_id: str
    status: str


class SendEventRequest(BaseModel):
    event_type: str
    payload: dict


class SagaStatusResponse(BaseModel):
    saga_id: str
    saga_type: str
    status: str
    state: dict | None = None


# --- Saga registry ---
SAGA_REGISTRY = {
    "OrderFulfillmentSaga": OrderFulfillmentSaga,
    "TimeoutSaga": TimeoutSaga,
    "CompensationChainSaga": CompensationChainSaga,
    "ParallelStepsSaga": ParallelStepsSaga,
    "EscalationSaga": EscalationSaga,
}


@app.post("/sagas/start", response_model=StartSagaResponse)
def start_saga(req: StartSagaRequest) -> StartSagaResponse:
    """Start a new saga by type and input."""
    saga_cls = SAGA_REGISTRY.get(req.saga_type)
    if not saga_cls:
        logger.warning(f"Unknown saga type: {req.saga_type}")
        raise HTTPException(
            status_code=400, detail=f"Unknown saga type: {req.saga_type}"
        )
    try:
        saga = saga_cls(**req.input)
        saga_id = manager.start_saga(saga)
        logger.info(f"Started saga {saga_id} of type {req.saga_type}")
        return StartSagaResponse(saga_id=saga_id, status="started")
    except Exception as exc:
        logger.error(f"Failed to start saga: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to start saga: {exc}")


@app.post("/sagas/{saga_id}/send")
def send_event(saga_id: str, req: SendEventRequest) -> dict:
    """Send an event to a saga."""
    try:
        result = manager.send_event(saga_id, req.event_type, req.payload)
        logger.info(f"Sent event {req.event_type} to saga {saga_id}")
        return {"result": result}
    except Exception as exc:
        logger.error(f"Failed to send event: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to send event: {exc}")


@app.get("/sagas/{saga_id}", response_model=SagaStatusResponse)
def get_saga_status(saga_id: str) -> SagaStatusResponse:
    """Query saga status."""
    saga = manager.get_saga(saga_id)
    if not saga:
        logger.warning(f"Saga not found: {saga_id}")
        raise HTTPException(status_code=404, detail=f"Saga not found: {saga_id}")
    return SagaStatusResponse(
        saga_id=saga_id,
        saga_type=type(saga).__name__,
        status=getattr(saga, "status", "unknown"),
        state=saga.model_dump() if hasattr(saga, "model_dump") else None,
    )


# Register all advanced saga patterns
manager.register_saga(OrderFulfillmentSaga)
manager.register_saga(TimeoutSaga)
manager.register_saga(CompensationChainSaga)
manager.register_saga(ParallelStepsSaga)
manager.register_saga(EscalationSaga)


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
