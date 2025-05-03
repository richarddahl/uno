"""
Unit tests for saga structured logging and logger injection.
"""

import pytest
from uno.infrastructure.logging import LoggerService
from examples.app.sagas.saga_logging import get_saga_logger
from examples.app.sagas.order_fulfillment_saga import OrderFulfillmentSaga
from examples.app.sagas.timeout_saga import TimeoutSaga
from examples.app.sagas.compensation_chain_saga import CompensationChainSaga
from examples.app.sagas.parallel_steps_saga import ParallelStepsSaga
from examples.app.sagas.escalation_saga import EscalationSaga


class FakeLogger(LoggerService):
    def __init__(self):
        self.records = []

    def structured_log(self, level: str, msg: str, **kwargs):
        self.records.append((level, msg, kwargs))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "SagaClass,init_event",
    [
        (OrderFulfillmentSaga, {"type": "OrderPlaced", "order_id": "log-1"}),
        (TimeoutSaga, {"type": "Timeout"}),
        (CompensationChainSaga, {"type": "Step1Completed"}),
        (ParallelStepsSaga, {"type": "StepACompleted"}),
        (EscalationSaga, {"type": "StepFailed"}),
    ],
)
async def test_saga_structured_logging(SagaClass, init_event):
    logger = FakeLogger()
    saga = SagaClass(logger=logger)
    await saga.handle_event(init_event)
    assert logger.records, f"No logs captured for {SagaClass.__name__}"
    # Check that the log contains expected keys
    found = any("event_type" in rec[2] for rec in logger.records)
    assert found, f"Structured log missing event_type for {SagaClass.__name__}"


def test_get_saga_logger_returns_logger():
    logger = get_saga_logger("test")
    assert isinstance(logger, LoggerService)
