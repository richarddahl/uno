import pytest
from uno.core.events.middleware.circuit_breaker import CircuitBreakerMiddleware, CircuitBreakerState
from uno.core.events.handlers import EventHandlerContext
from uno.core.errors.result import Success, Failure, Result
from uno.core.logging.logger import LoggerService, LoggingConfig
from uno.core.events.base_event import DomainEvent

class FakeEvent(DomainEvent):
    event_type: str = "FakeEvent"
    event_id: str = "fake-id"
    aggregate_id: str = "agg-id"

class FakeLoggerService(LoggerService):
    def __init__(self) -> None:
        super().__init__(LoggingConfig())
        self.structured_log_calls: list[tuple[str, str, dict[str, object]]] = []
    def structured_log(self, level: str, message: str, **kwargs: object) -> None:
        self.structured_log_calls.append((level, message, kwargs))

@pytest.fixture
def fake_logger() -> FakeLoggerService:
    return FakeLoggerService()

@pytest.mark.asyncio
async def test_circuit_breaker_blocks_after_failures(fake_logger: FakeLoggerService) -> None:
    middleware = CircuitBreakerMiddleware(logger=fake_logger, event_types=["FakeEvent"], options=CircuitBreakerState(failure_threshold=2, recovery_timeout_seconds=1000))
    event = FakeEvent()
    context = EventHandlerContext(event=event)
    async def failing_handler(ctx: EventHandlerContext) -> Failure[str, Exception]:
        return Failure(Exception("fail"))
    await middleware.process(context, failing_handler)
    await middleware.process(context, failing_handler)
    result = await middleware.process(context, failing_handler)
    assert result.is_failure
    assert "Circuit open for event type" in str(result.error)
    found = any("circuit open" in call[1].lower() for call in fake_logger.structured_log_calls)
    assert found

@pytest.mark.asyncio
async def test_circuit_breaker_recovers_after_timeout(fake_logger: FakeLoggerService) -> None:
    middleware = CircuitBreakerMiddleware(logger=fake_logger, event_types=["FakeEvent"], options=CircuitBreakerState(failure_threshold=1, recovery_timeout_seconds=0.01))
    event = FakeEvent()
    context = EventHandlerContext(event=event)
    async def failing_handler(ctx: EventHandlerContext) -> Failure[str, Exception]:
        return Failure(Exception("fail"))
    async def succeeding_handler(ctx: EventHandlerContext) -> Success[str, Exception]:
        return Success("ok")
    await middleware.process(context, failing_handler)
    import asyncio
    await asyncio.sleep(0.02)
    result = await middleware.process(context, succeeding_handler)
    assert result.is_success
    state = middleware.circuit_states[event.event_type]
    assert state.state == CircuitBreakerState.CLOSED

@pytest.mark.asyncio
async def test_circuit_breaker_passes_success(fake_logger: FakeLoggerService) -> None:
    middleware = CircuitBreakerMiddleware(logger=fake_logger, event_types=["FakeEvent"])
    event = FakeEvent()
    context = EventHandlerContext(event=event)
    async def succeeding_handler(ctx: EventHandlerContext) -> Success[str, Exception]:
        return Success("ok")
    result = await middleware.process(context, succeeding_handler)
    assert result.is_success
    state = middleware.circuit_states[event.event_type]
    assert state.failure_count == 0
    assert state.state == CircuitBreakerState.CLOSED
