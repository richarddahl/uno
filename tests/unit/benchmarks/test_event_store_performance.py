"""Performance benchmarks for event store implementations.

This module contains benchmarks for measuring the performance of different
event store implementations (PostgreSQL, Redis) using the same test cases.
"""

from __future__ import annotations

import asyncio
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime, timezone
from typing import (
    Any,
    AsyncIterator,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    cast,
    overload,
)

import pytest
from pydantic import BaseModel, Field, ConfigDict

from uno.event_store.base import DomainEvent, EventStore
from uno.injection import ContainerProtocol
from uno.logging.protocols import LoggerProtocol

# Type variable for event types
E = TypeVar("E", bound=DomainEvent)


# Benchmark configuration
@dataclass
class BenchmarkConfig:
    """Configuration for benchmark tests."""

    num_events: int = 10_000
    batch_size: int = 100
    warmup_runs: int = 3
    test_runs: int = 5


# Default benchmark configuration
DEFAULT_CONFIG = BenchmarkConfig()


class MockEventStore(EventStore[DomainEvent], ABC):
    """Base mock event store for benchmarking."""

    def __init__(
        self, container: ContainerProtocol, settings: Any, logger: LoggerProtocol
    ) -> None:
        self._container = container
        self._settings = settings
        self._logger = logger
        self._events: Dict[str, List[DomainEvent]] = defaultdict(list)
        self._connected = False

    @property
    def container(self) -> ContainerProtocol:
        return self._container

    @property
    def settings(self) -> Any:
        return self._settings

    @property
    def logger(self) -> LoggerProtocol:
        return self._logger

    async def connect(self) -> None:
        """Connect to the event store."""
        self._connected = True

    async def disconnect(self) -> None:
        """Disconnect from the event store."""
        self._connected = False

    async def close(self) -> None:
        """Close the event store."""
        await self.disconnect()

    async def get_events(self, aggregate_id: str) -> AsyncIterator[DomainEvent]:
        """Get all events for an aggregate."""
        for event in self._events.get(aggregate_id, []):
            yield event

    async def get_events_of_type(
        self, event_type: Type[DomainEvent]
    ) -> AsyncIterator[DomainEvent]:
        """Get all events of a specific type."""
        for events in self._events.values():
            for event in events:
                if isinstance(event, event_type):
                    yield event

    async def get_events_by_aggregate_type(
        self, aggregate_type: str
    ) -> AsyncIterator[DomainEvent]:
        """Get all events for an aggregate type."""
        for aggregate_id, events in self._events.items():
            if aggregate_id.startswith(f"{aggregate_type}:"):
                for event in events:
                    yield event

    async def get_last_event(self, aggregate_id: str) -> DomainEvent | None:
        """Get the last event for an aggregate."""
        events = self._events.get(aggregate_id, [])
        return events[-1] if events else None

    async def get_aggregate_version(self, aggregate_id: str) -> int:
        """Get the current version of an aggregate."""
        return len(self._events.get(aggregate_id, []))

    async def optimize(self) -> None:
        """Optimize the event store."""
        pass

    async def append(
        self, events: list[DomainEvent], expected_version: int | None = None
    ) -> None:
        """Append events to the store."""
        if not events:
            return

        aggregate_id = events[0].aggregate_id
        current_version = await self.get_aggregate_version(aggregate_id)

        if expected_version is not None and current_version != expected_version:
            raise ValueError(
                f"Version conflict: expected {expected_version}, got {current_version}"
            )

        self._events[aggregate_id].extend(events)

    async def get_event_stream(self, aggregate_id: str) -> AsyncIterator[DomainEvent]:
        """Get a stream of events for an aggregate."""
        for event in self._events.get(aggregate_id, []):
            yield event

    async def get_snapshot(self, aggregate_id: str) -> DomainEvent | None:
        """Get the latest snapshot for an aggregate."""
        events = self._events.get(aggregate_id, [])
        return events[-1] if events else None

    async def clear(self) -> None:
        """Clear all events from the store (for testing)."""
        self._events.clear()


class MockPostgreSQLEventStore(MockEventStore):
    """Mock PostgreSQL event store for benchmarking."""

    async def optimize(self) -> None:
        """Optimize the PostgreSQL event store."""
        # Add any PostgreSQL-specific optimizations here
        await super().optimize()


class MockRedisEventStore(MockEventStore):
    """Mock Redis event store for benchmarking."""

    async def optimize(self) -> None:
        """Optimize the Redis event store."""
        # Add any Redis-specific optimizations here
        await super().optimize()


# Test configuration
NUM_EVENTS = 1_000  # Reduced for faster test execution
BATCH_SIZE = 100  # Batch size for bulk operations


# Test event class
class BenchmarkEvent(DomainEvent):
    """A simple event for benchmarking purposes."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    aggregate_id: str = Field(default_factory=lambda: f"test-{uuid.uuid4()}")
    aggregate_version: int = 1
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: Dict[str, Any] = Field(default_factory=dict)

    @property
    def event_type(self) -> str:
        """Get the event type."""
        return self.__class__.__name__

    @property
    def metadata(self) -> Dict[str, Any]:
        """Get the event metadata."""
        return {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert the event to a dictionary."""
        return {
            "event_id": self.event_id,
            "aggregate_id": self.aggregate_id,
            "aggregate_version": self.aggregate_version,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "data": self.data,
        }


@dataclass
class BenchmarkResult:
    """Result of a benchmark operation."""

    operation: str
    store_type: str
    duration: float
    event_count: int = 0
    metadata: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        metadata = f" ({self.metadata})" if self.metadata else ""
        return (
            f"{self.store_type} - {self.operation}: "
            f"{self.duration:.4f}s for {self.event_count} events"
            f"{metadata}"
        )


class EventStoreBenchmark:
    """Benchmark suite for event store implementations."""

    def __init__(self, store: EventStore[E], store_name: str = "EventStore") -> None:
        self.store = store
        self.store_name = store_name
        self.aggregate_id = uuid.uuid4()
        self.results: List[Dict[str, Any]] = []

    async def setup(self) -> None:
        """Set up the benchmark."""
        if hasattr(self.store, "connect"):
            await self.store.connect()

    async def teardown(self) -> None:
        """Clean up after the benchmark."""
        if hasattr(self.store, "disconnect"):
            await self.store.disconnect()

    async def _time_operation(
        self, operation_name: str, operation: Any, *args: Any, **kwargs: Any
    ) -> BenchmarkResult:
        """Time an operation and return the result."""
        start_time = asyncio.get_event_loop().time()
        result = await operation(*args, **kwargs)
        end_time = asyncio.get_event_loop().time()

        return BenchmarkResult(
            operation=operation_name,
            store_type=self.store_name,
            duration=end_time - start_time,
            event_count=getattr(result, "event_count", 0),
            metadata=getattr(result, "metadata", None),
        )

    async def benchmark_append_events(
        self, store: EventStore[E], aggregate_id: str, num_events: int
    ) -> None:
        """Benchmark appending multiple events."""
        events = [
            BenchmarkEvent(
                aggregate_id=aggregate_id,
                aggregate_version=i + 1,
                timestamp=datetime.now(timezone.utc),
                data={"event_number": i, "data": "x" * 100},
            )
            for i in range(num_events)
        ]

        # Time the append operation
        start_time = asyncio.get_event_loop().time()
        await store.append(events=events, expected_version=0)
        end_time = asyncio.get_event_loop().time()

        # Store the result
        self.results.append(
            {
                "operation": f"append_{num_events}_events",
                "time_seconds": end_time - start_time,
                "events_per_second": (
                    num_events / (end_time - start_time)
                    if (end_time - start_time) > 0
                    else 0
                ),
            }
        )

    async def benchmark_append_batch(
        self, store: EventStore[E], aggregate_id: str, num_events: int, batch_size: int
    ) -> None:
        """Benchmark appending events in batches."""
        # Create all events first
        all_events = [
            [
                BenchmarkEvent(
                    aggregate_id=aggregate_id,
                    aggregate_version=i * batch_size + j + 1,
                    timestamp=datetime.now(timezone.utc),
                    data={"batch": i, "event": j, "data": "x" * 100},
                )
                for j in range(batch_size)
            ]
            for i in range(num_events // batch_size)
        ]

        # Time the batch append operations
        start_time = asyncio.get_event_loop().time()
        for i, batch in enumerate(all_events):
            await store.append(events=batch, expected_version=i * batch_size)
        end_time = asyncio.get_event_loop().time()

        # Store the result
        self.results.append(
            {
                "operation": f"batch_append_{len(all_events)}_batches_of_{batch_size}",
                "time_seconds": end_time - start_time,
                "events_per_second": (
                    num_events / (end_time - start_time)
                    if (end_time - start_time) > 0
                    else 0
                ),
            }
        )

    async def _read_all(self, events: AsyncIterator[E]) -> List[E]:
        """Helper to read all events from an async iterator."""
        result: List[E] = []
        async for event in events:
            result.append(event)
        return result

    async def benchmark_read_all(self) -> BenchmarkResult:
        """Benchmark reading all events for an aggregate."""
        # First append some test data
        await self.benchmark_append_events(self.store, str(self.aggregate_id), 1000)

        # Time the read operation
        start_time = asyncio.get_event_loop().time()
        events = await self._read_all(
            await self.store.get_events(aggregate_id=str(self.aggregate_id))
        )
        end_time = asyncio.get_event_loop().time()

        return BenchmarkResult(
            operation="read_all",
            store_type=self.store_name,
            duration=end_time - start_time,
            event_count=len(events),
            metadata={"event_count": len(events)},
        )


# Create test event store fixtures
@pytest.fixture
async def postgres_store(mock_container, mock_settings, mock_logger):
    """Create a mock PostgreSQL event store for benchmarking."""
    store = MockPostgreSQLEventStore[BenchmarkEvent](
        container=mock_container, settings=mock_settings, logger=mock_logger
    )
    await store.connect()
    try:
        yield store
    finally:
        await store.disconnect()


@pytest.fixture
async def redis_store(mock_container, mock_settings, mock_logger):
    """Create a mock Redis event store for benchmarking."""
    store = MockRedisEventStore[BenchmarkEvent](
        container=mock_container, settings=mock_settings, logger=mock_logger
    )
    await store.connect()
    try:
        yield store
    finally:
        await store.disconnect()


# Benchmark tests for each store
@pytest.mark.benchmark
async def test_benchmark_postgres(
    postgres_store: PostgreSQLEventStore[BenchmarkEvent],
) -> None:
    """Run all benchmarks for PostgreSQL event store."""
    benchmark = EventStoreBenchmark(postgres_store, "PostgreSQL")
    await benchmark.setup()
    try:
        print(await benchmark.benchmark_append_single(1000))
        print(await benchmark.benchmark_append_batch(100))
        print(await benchmark.benchmark_read_all())
    finally:
        await benchmark.teardown()


@pytest.mark.benchmark
async def test_benchmark_redis(redis_store: RedisEventStore[BenchmarkEvent]) -> None:
    """Run all benchmarks for Redis event store."""
    benchmark = EventStoreBenchmark(redis_store, "Redis")
    await benchmark.setup()
    try:
        print(await benchmark.benchmark_append_single(1000))
        print(await benchmark.benchmark_append_batch(100))
        print(await benchmark.benchmark_read_all())
    finally:
        await benchmark.teardown()


if __name__ == "__main__":
    import asyncio
    import sys
    import pytest

    # Run the benchmarks using pytest
    exit_code = pytest.main(
        [
            __file__,
            "-v",
            "-s",  # Show output
            "--durations=10",  # Show 10 slowest tests
        ]
    )

    sys.exit(exit_code)
