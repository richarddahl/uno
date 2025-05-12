import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest

from uno.metrics.collector import AsyncMetricCollector, AsyncMetricReporter
from uno.metrics.implementations.memory import InMemoryMetricStore
from uno.metrics.protocols import (
    CounterProtocol,
    GaugeProtocol,
    MetricProtocol,
    TimerContext,
    TimerProtocol,
)
from uno.metrics.registry import MetricRegistry


@pytest.fixture
async def registry() -> MetricRegistry:
    """Create a metric registry fixture."""
    return MetricRegistry()


@pytest.fixture
async def memory_store() -> InMemoryMetricStore:
    """Create an in-memory metric store fixture."""
    return InMemoryMetricStore()


@pytest.fixture
async def async_reporter(memory_store) -> AsyncMetricReporter:
    """Create an async metric reporter fixture."""
    reporter = AsyncMetricReporter(interval=0.1)
    await reporter.add_backend(memory_store)
    return reporter


@pytest.mark.asyncio
async def test_metric_registry(registry: MetricRegistry) -> None:
    """Test metric registry functionality."""

    # Test registration
    class TestMetric(MetricProtocol):
        async def get_value(self) -> Any:
            return 42

    metric = TestMetric()
    registry.register("test", metric)
    assert "test" in registry
    assert registry.get("test") == metric

    # Test removal
    registry.remove("test")
    assert "test" not in registry

    # Test snapshot
    registry.register("test", metric)
    snapshot = await registry.async_snapshot()
    assert "test" in snapshot
    # Await the coroutine to get the actual value
    assert await snapshot["test"] == 42


@pytest.mark.asyncio
async def test_async_metric_collector() -> None:
    """Test async metric collector."""

    class TestCollector(AsyncMetricCollector):
        async def _collect_metrics(self) -> Dict[str, Any]:
            return {"test": 42}

        async def _process_metrics(self, metrics: Dict[str, Any]) -> None:
            self._processed = metrics

    collector = TestCollector(interval=0.1)
    collector._processed = None

    # Start collection
    await collector.start()
    await asyncio.sleep(0.2)  # Wait for one collection cycle

    # Verify metrics were collected
    assert collector._processed is not None
    assert collector._processed["test"] == 42

    # Stop collection
    await collector.stop()


@pytest.mark.asyncio
async def test_async_metric_reporter(
    async_reporter: AsyncMetricReporter,
    memory_store: InMemoryMetricStore,
) -> None:
    """Test async metric reporter."""
    # Start reporter
    await async_reporter.start()

    # Report metrics
    metrics = {"test": 42}
    await async_reporter._collect_metrics()  # Force collection
    await asyncio.sleep(0.1)  # Wait for reporting

    # Verify metrics were reported
    stored_metrics = await memory_store.retrieve()
    assert "test" in stored_metrics
    assert stored_metrics["test"] == 42

    # Stop reporter
    await async_reporter.stop()


@pytest.mark.asyncio
async def test_counter_protocol() -> None:
    """Test counter protocol implementation."""

    class TestCounter(CounterProtocol):
        def __init__(self) -> None:
            self._count = 0

        async def inc(self, amount: float = 1.0) -> None:
            self._count += amount

        async def dec(self, amount: float = 1.0) -> None:
            self._count -= amount

        async def get_value(self) -> Any:
            return self._count

    counter = TestCounter()
    await counter.inc()
    await counter.inc(2.0)
    await counter.dec()
    assert await counter.get_value() == 2.0


@pytest.mark.asyncio
async def test_gauge_protocol() -> None:
    """Test gauge protocol implementation."""

    class TestGauge(GaugeProtocol):
        def __init__(self) -> None:
            self._value = 0.0

        async def set(self, value: float) -> None:
            self._value = value

        async def inc(self, amount: float = 1.0) -> None:
            self._value += amount

        async def dec(self, amount: float = 1.0) -> None:
            self._value -= amount

        async def get_value(self) -> Any:
            return self._value

    gauge = TestGauge()
    await gauge.set(10.0)
    await gauge.inc(5.0)
    await gauge.dec(2.0)
    assert await gauge.get_value() == 13.0


@pytest.mark.asyncio
async def test_timer_protocol() -> None:
    """Test timer protocol implementation."""

    class TestTimer(TimerProtocol, MetricProtocol):
        def __init__(self) -> None:
            self._durations: list[float] = []
            self._lock = asyncio.Lock()

        async def time(self) -> TimerContext:
            # Implementation of time method
            class Context(TimerContext):
                def __init__(self, timer: "TestTimer") -> None:
                    self.timer = timer
                    self.start_time = 0.0

                async def __aenter__(self) -> "Context":
                    self.start_time = asyncio.get_event_loop().time()
                    return self

                async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
                    duration = asyncio.get_event_loop().time() - self.start_time
                    async with self.timer._lock:
                        self.timer._durations.append(duration)

            return Context(self)

        async def record(self, duration: float) -> None:
            async with self._lock:
                self._durations.append(duration)

        async def get_value(self) -> dict[str, float]:
            async with self._lock:
                if not self._durations:
                    return {
                        "min": 0.0,
                        "max": 0.0,
                        "mean": 0.0,
                        "count": 0,
                    }

                durations = self._durations
                return {
                    "min": min(durations),
                    "max": max(durations),
                    "mean": sum(durations) / len(durations),
                    "count": len(durations),
                }

    timer = TestTimer()

    # Test timing context
    async with await timer.time():
        await asyncio.sleep(0.1)

    # Test direct recording
    await timer.record(0.2)

    # Verify values
    value = await timer.get_value()
    assert value["count"] == 2
    assert value["min"] <= 0.11  # Allow a small buffer for timing variations
    assert value["max"] >= 0.2
    assert value["mean"] >= 0.15
