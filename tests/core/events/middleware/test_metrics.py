import asyncio
from typing import Any, ClassVar

import pytest

from uno.core.errors.result import Failure, Success
from uno.core.events.base_event import DomainEvent
from uno.core.events.handlers import EventHandlerContext
from uno.core.events.middleware.metrics import EventMetrics, MetricsMiddleware
from uno.infrastructure.logging.logger import LoggerService, LoggingConfig


class FakeEvent(DomainEvent):
    event_type: ClassVar[str] = "FakeEvent"
    version: int = 1


class FakeLoggerService(LoggerService):
    structured_log_calls: list[tuple[str, str, dict[str, Any]]]

    def __init__(self) -> None:
        super().__init__(LoggingConfig())
        self.structured_log_calls = []

    def structured_log(
        self, level: str, message: str, *args: object, **kwargs: object
    ) -> None:
        self.structured_log_calls.append((level, message, kwargs))


@pytest.fixture
def fake_logger() -> FakeLoggerService:
    logger = FakeLoggerService()
    asyncio.run(logger.initialize())
    yield logger
    asyncio.run(logger.dispose())


@pytest.mark.asyncio
async def test_metrics_middleware_records_success_and_failure(
    fake_logger: FakeLoggerService,
) -> None:
    # Arrange
    middleware = MetricsMiddleware(logger=fake_logger, report_interval_seconds=0.01)
    event = FakeEvent()
    context = EventHandlerContext(event=event)

    async def succeeding_handler(ctx: EventHandlerContext) -> Success[str, Exception]:
        return Success("ok")

    async def failing_handler(ctx: EventHandlerContext) -> Failure[str, Exception]:
        return Failure(Exception("fail"))

    # Act
    await middleware.process(context, succeeding_handler)
    await middleware.process(context, failing_handler)
    # Assert
    key = event.__class__.__name__
    if key not in middleware.metrics:
        print("Available metrics keys:", list(middleware.metrics.keys()))
    metrics = middleware.metrics[key]
    if metrics.count != 2:
        print("Metrics:", metrics)
    assert metrics.count == 2
    assert metrics.success_count == 1
    assert metrics.failure_count == 1
    assert metrics.min_duration_ms >= 0
    assert metrics.max_duration_ms >= metrics.min_duration_ms
    assert metrics.average_duration_ms >= 0
    # Check logger calls for reporting
    if not any(
        "metrics" in call[1].lower() for call in fake_logger.structured_log_calls
    ):
        print("Log calls:", fake_logger.structured_log_calls)
    found = any(
        "metrics" in call[1].lower() for call in fake_logger.structured_log_calls
    )
    assert found or middleware.last_report_time > 0


@pytest.mark.asyncio
async def test_metrics_middleware_logs_report(fake_logger: FakeLoggerService) -> None:
    # Arrange
    middleware = MetricsMiddleware(logger=fake_logger, report_interval_seconds=0.0)
    event = FakeEvent()
    context = EventHandlerContext(event=event)

    async def handler(ctx: EventHandlerContext) -> Success[str, Exception]:
        return Success("ok")

    # Act
    await middleware.process(context, handler)
    # Assert
    # Should log a metrics report immediately due to interval=0.0
    if not any(
        "metrics" in call[1].lower() for call in fake_logger.structured_log_calls
    ):
        print("Log calls:", fake_logger.structured_log_calls)
    assert any(
        "metrics" in call[1].lower() for call in fake_logger.structured_log_calls
    )


@pytest.mark.asyncio
async def test_event_metrics_properties() -> None:
    metrics = EventMetrics()
    assert metrics.average_duration_ms == 0.0
    assert metrics.success_rate == 0.0
    metrics.record(10.0, True)
    metrics.record(20.0, False)
    assert metrics.count == 2
    assert metrics.average_duration_ms == 15.0
    assert metrics.success_rate == 50.0
    assert metrics.min_duration_ms == 10.0
    assert metrics.max_duration_ms == 20.0
