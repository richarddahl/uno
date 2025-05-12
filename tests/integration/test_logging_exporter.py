import pytest
from uno.metrics.backends.logging import LoggingReporter, LogConfig
from uno.metrics.types import Counter, Gauge

@pytest.fixture
def reporter() -> LoggingReporter:
    return LoggingReporter(LogConfig())

from typing import ClassVar, Any

class FakeCounter:
    name: ClassVar[str] = "test_counter"
    description: ClassVar[str] = "A test counter"
    tags: dict[str, str]
    _value: float
    def __init__(self) -> None:
        self.tags = {}
        self._value = 0.0
    async def increment(self, amount: float) -> None:
        self._value += amount
    async def get_value(self) -> float:
        return self._value

class FakeGauge:
    name: ClassVar[str] = "test_gauge"
    description: ClassVar[str] = "A test gauge"
    tags: dict[str, str]
    _value: float
    def __init__(self) -> None:
        self.tags = {}
        self._value = 0.0
    async def set(self, value: float) -> None:
        self._value = value
    async def get_value(self) -> float:
        return self._value

async def make_metric(kind: str, value: float, tags: dict[str, str]) -> Any:
    if kind == "counter":
        metric = FakeCounter()
        metric.tags = tags
        await metric.increment(value)
    elif kind == "gauge":
        metric = FakeGauge()
        metric.tags = tags
        await metric.set(value)
    else:
        raise ValueError(f"Unknown metric kind: {kind}")
    return metric

import pytest

@pytest.mark.asyncio
async def test_logging_exporter_basic(reporter: LoggingReporter, capfd) -> None:
    metric = await make_metric("counter", 5, {"env": "test"})
    await reporter.report([metric])
    out = capfd.readouterr().out
    assert "test_counter" in out, "Metric name should appear in log output."

@pytest.mark.asyncio
async def test_logging_exporter_tags(reporter: LoggingReporter, capfd) -> None:
    metric = await make_metric("gauge", 3.14, {"service": "integration", "env": "dev"})
    await reporter.report([metric])
    out = capfd.readouterr().out
    assert "service" in out and "integration" in out, "Tags should appear in log output."

@pytest.mark.asyncio
async def test_logging_exporter_error_handling(reporter: LoggingReporter, capfd) -> None:
    class FakeMetric:
        name: None = None
        description: str = "No name"
        tags: dict[str, str] = {}
        def get_value(self) -> int:
            return 42
    # Should not raise, but should log something with missing name
    await reporter.report([FakeMetric()])
    out = capfd.readouterr().out
    assert "No name" in out, "Even invalid metrics should be logged."

@pytest.mark.asyncio
async def test_logging_exporter_edge_case_empty_tags(reporter: LoggingReporter, capfd) -> None:
    metric = await make_metric("gauge", 1.23, {})
    await reporter.report([metric])
    out = capfd.readouterr().out
    assert "test_gauge" in out, "Metric with empty tags should still be logged."
