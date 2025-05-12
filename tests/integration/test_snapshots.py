"""
Integration tests for Uno event snapshot management.
Covers CompositeSnapshotStrategy, EventCountSnapshotStrategy, TimeBasedSnapshotStrategy, and SnapshotStore implementations.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Coroutine
from datetime import UTC, datetime, timedelta
from typing import Any, TypeVar, cast, ParamSpec

import pytest

from tests.integration.fake_logger import FakeLogger
from uno.snapshots.implementations.memory import (
    CompositeSnapshotStrategy,
    EventCountSnapshotStrategy,
    InMemorySnapshotStore,
    TimeBasedSnapshotStrategy,
)

# Type variable for async test functions
T = TypeVar('T', bound=Callable[..., Awaitable[Any]])

# Type alias for async test functions
type AsyncTestFunc = Callable[..., Coroutine[Any, Any, None]]

# Type variable for test functions with any parameters
P = ParamSpec('P')

def asyncio_test(
    func: Callable[P, Awaitable[Any]] | T,
) -> Callable[P, Coroutine[Any, Any, Any]] | T:
    """Type-annotated wrapper for @pytest.mark.asyncio.
    
    This is needed because the pytest-asyncio plugin doesn't have type stubs.
    """
    # The type ignore is needed because pytest.mark.asyncio doesn't have type stubs
    decorated = pytest.mark.asyncio(func)  # type: ignore[no-any-return,no-untyped-call]
    return cast('T', decorated)


class FakeAggregate:
    def __init__(self, aggregate_id: str, state: Any) -> None:
        self.id = aggregate_id
        self.aggregate_id = aggregate_id  # Adding this for compatibility
        self.state = state
        self.version = 1


class FakeEvent:
    def __init__(
        self, aggregate_id: str, version: int, data: dict[str, Any] | None = None
    ) -> None:
        self.aggregate_id = aggregate_id
        self.version = version
        self.data = data or {}
        self.event_type = "FakeEvent"


@asyncio_test
async def test_event_count_snapshot_strategy() -> None:
    """Test EventCountSnapshotStrategy's snapshot decision based on event count."""
    strategy = EventCountSnapshotStrategy(threshold=3)
    # 0 events since last snapshot
    assert not await strategy.should_snapshot("agg1", 0)
    # 2 events since last snapshot
    assert not await strategy.should_snapshot("agg1", 2)
    # 3 events since last snapshot
    assert await strategy.should_snapshot("agg1", 3)
    # 4 events since last snapshot
    assert await strategy.should_snapshot("agg1", 4)


@asyncio_test
async def test_time_based_snapshot_strategy() -> None:
    """Test TimeBasedSnapshotStrategy's snapshot decision based on time."""
    strategy = TimeBasedSnapshotStrategy(minutes_threshold=1)
    # Should snapshot if never before
    assert await strategy.should_snapshot("agg1", 0)
    # Simulate recent snapshot (should not trigger)
    strategy._last_snapshot_time["agg1"] = datetime.now(UTC)
    assert not await strategy.should_snapshot("agg1", 0)
    # Simulate old snapshot (should trigger)
    strategy._last_snapshot_time["agg1"] = datetime.now(UTC) - timedelta(minutes=2)
    assert await strategy.should_snapshot("agg1", 0)


@asyncio_test
async def test_composite_snapshot_strategy() -> None:
    """Test CompositeSnapshotStrategy's snapshot decision based on multiple strategies."""
    # Create a composite strategy with two strategies
    # that should trigger a snapshot if either one returns True
    # EventCountSnapshotStrategy with threshold of 2
    # TimeBasedSnapshotStrategy with 1 minute threshold
    count_strategy = EventCountSnapshotStrategy(threshold=2)
    time_strategy = TimeBasedSnapshotStrategy(minutes_threshold=1)
    composite = CompositeSnapshotStrategy([count_strategy, time_strategy])
    # Should snapshot if any strategy returns True
    assert await composite.should_snapshot("agg1", 2)
    # Should not snapshot if none return True
    # Simulate recent snapshot for time strategy
    time_strategy._last_snapshot_time["agg1"] = datetime.now(UTC)
    assert not await composite.should_snapshot("agg1", 1)


@asyncio_test
async def test_in_memory_snapshot_store_save_and_get() -> None:
    """Test saving and retrieving a snapshot from InMemorySnapshotStore."""
    store = InMemorySnapshotStore(FakeLogger())
    agg = FakeAggregate("agg1", "foo")
    await store.save_snapshot(agg)
    loaded = await store.get_snapshot("agg1", type(agg))
    assert loaded is not None
    assert loaded.aggregate_id == "agg1"
    assert loaded.state == "foo"
    # Should return None for unknown id
    assert await store.get_snapshot("unknown", type(agg)) is None


@asyncio_test
async def test_in_memory_snapshot_store_overwrite() -> None:
    """Test that saving a snapshot with the same aggregate ID overwrites the existing one."""
    store = InMemorySnapshotStore(FakeLogger())
    aggregate_id = "agg1"
    snapshot1 = FakeAggregate(aggregate_id, "state1")
    snapshot2 = FakeAggregate(aggregate_id, "state2")

    await store.save_snapshot(snapshot1)
    stored_snapshot1 = await store.get_snapshot(aggregate_id)
    assert stored_snapshot1 is not None
    assert stored_snapshot1.state == "state1"

    await store.save_snapshot(snapshot2)
    stored_snapshot2 = await store.get_snapshot(aggregate_id)
    assert stored_snapshot2 is not None
    assert stored_snapshot2.state == "state2"


@asyncio_test
async def test_in_memory_snapshot_store_delete() -> None:
    """Test that snapshots can be deleted from the store."""
    store = InMemorySnapshotStore(FakeLogger())
    agg = FakeAggregate("agg1", "foo")
    await store.save_snapshot(agg)

    # Verify snapshot exists
    assert await store.get_snapshot("agg1") is not None

    # Delete snapshot
    await store.delete_snapshots("agg1")

    # Verify snapshot no longer exists
    assert await store.get_snapshot("agg1") is None


@asyncio_test
async def test_snapshot_store_with_multiple_versions() -> None:
    """Test that snapshot store correctly handles multiple versions of the same aggregate."""
    store = InMemorySnapshotStore(FakeLogger())

    # Save multiple versions
    aggregate_id = "test-aggregate"

    # Save version 1
    await store.save_snapshot(aggregate_id, 1, {"counter": 1})

    # Save version 2
    await store.save_snapshot(aggregate_id, 2, {"counter": 2})

    # Save version 5 (skip versions to test ordering)
    await store.save_snapshot(aggregate_id, 5, {"counter": 5})

    # Verify we get the latest version (5)
    latest = await store.get_snapshot(aggregate_id)
    assert latest is not None
    assert latest.aggregate_version == 5
    assert latest.state["counter"] == 5


@asyncio_test
async def test_snapshot_integration_with_complex_state() -> None:
    """Test snapshots with more complex nested state structures."""
    store = InMemorySnapshotStore(FakeLogger())

    # Create a complex state object
    complex_state = {
        "name": "Test Entity",
        "attributes": {
            "active": True,
            "tags": ["test", "snapshot", "complex"],
            "metadata": {
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-02T00:00:00",
            },
        },
        "items": [{"id": 1, "value": "one"}, {"id": 2, "value": "two"}],
    }

    aggregate_id = "complex-aggregate"

    # Save snapshot with complex state
    await store.save_snapshot(aggregate_id, 1, complex_state)

    # Retrieve the snapshot
    snapshot = await store.get_snapshot(aggregate_id)

    # Verify complex state is preserved correctly
    assert snapshot is not None
    assert snapshot.state["name"] == "Test Entity"
    assert snapshot.state["attributes"]["active"] is True
    assert "test" in snapshot.state["attributes"]["tags"]
    assert len(snapshot.state["items"]) == 2
    assert snapshot.state["items"][1]["value"] == "two"


class AggregateWithEvents:
    """Simple aggregate that applies events to update its state."""

    def __init__(self, aggregate_id: str, state: dict[str, Any] | None = None) -> None:
        self.id = aggregate_id
        self.state = state or {"counter": 0, "events_applied": []}
        self.version = 0

    def apply_event(self, event: FakeEvent) -> None:
        """Apply an event to update the aggregate state."""
        # Update version
        self.version = event.version

        # Update state based on event
        if event.data.get("increment"):
            self.state["counter"] += event.data["increment"]

        # Record event application
        self.state["events_applied"].append(event.event_type + f"_v{event.version}")


@pytest.mark.asyncio
async def test_realistic_snapshot_integration() -> None:
    """
    Test a realistic integration scenario with event sourcing and snapshots.

    This test simulates:
    1. Creating an aggregate
    2. Applying several events to it
    3. Creating snapshots at specific intervals
    4. Reconstructing the aggregate from a snapshot + subsequent events
    """
    logger = FakeLogger()
    snapshot_store = InMemorySnapshotStore(logger)

    # Event store (simplified in-memory version for this test)
    events_by_aggregate: dict[str, list[FakeEvent]] = {}

    # Create snapshot strategy (snapshot every 3 events)
    snapshot_strategy = EventCountSnapshotStrategy(threshold=3)

    # Create an aggregate
    aggregate_id = "test-realistic"
    aggregate = AggregateWithEvents(aggregate_id)

    # Apply 5 events to the aggregate
    for i in range(1, 6):
        # Create event
        event = FakeEvent(
            aggregate_id=aggregate_id,
            version=i,  # Version increases with each event
            data={"increment": i},
        )

        # Apply event to aggregate
        aggregate.apply_event(event)

        # Store event
        if aggregate_id not in events_by_aggregate:
            events_by_aggregate[aggregate_id] = []
        events_by_aggregate[aggregate_id].append(event)

        # Check if we should take a snapshot
        if await snapshot_strategy.should_snapshot(aggregate_id, i):
            await snapshot_store.save_snapshot(
                aggregate, aggregate.version, aggregate.state
            )

    # Verify final state
    assert aggregate.state["counter"] == 15  # 1+2+3+4+5
    assert (
        len(aggregate.state["events_applied"]) == 5
    )  # Now simulate reconstructing the aggregate from a snapshot + events

    # Get the latest snapshot
    snapshot = await snapshot_store.get_snapshot(aggregate_id)
    assert snapshot is not None

    # The snapshot should be at version 3 because our snapshot strategy should trigger at version 3
    # (the EventCountSnapshotStrategy with threshold=3)
    snapshot_version = snapshot.aggregate_version

    # Reconstruct aggregate from snapshot
    reconstructed = AggregateWithEvents(aggregate_id, snapshot.state)
    reconstructed.version = snapshot.aggregate_version

    # Get events after the snapshot version
    remaining_events = [
        e
        for e in events_by_aggregate[aggregate_id]
        if e.version > reconstructed.version
    ]

    # Apply remaining events
    for event in remaining_events:
        reconstructed.apply_event(event)

    # Verify reconstructed aggregate matches original
    assert reconstructed.version == 5
    assert reconstructed.state["counter"] == 15
    assert len(reconstructed.state["events_applied"]) == 5
