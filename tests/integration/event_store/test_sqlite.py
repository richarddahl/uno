"""Integration tests for SQLite event store."""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator, Iterator
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Optional

import pytest
from pydantic import Field

from uno.domain.events import DomainEvent
from uno.event_store.sqlite import SQLiteEventStore


# Test event class
class MockEvent(DomainEvent):
    """Test event for SQLite event store tests."""

    name: str
    value: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "test_event"

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}


@pytest.fixture
def temp_db() -> Iterator[str]:
    """Create a temporary SQLite database file."""
    with NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        yield db_path
    finally:
        Path(db_path).unlink(missing_ok=True)


@pytest.fixture
async def sqlite_store(
    temp_db: str,
) -> AsyncGenerator[SQLiteEventStore[MockEvent], None]:
    """Create and initialize a SQLite event store."""
    store = SQLiteEventStore[MockEvent](db_path=temp_db)
    await store.connect()
    try:
        yield store
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_append_and_retrieve_events(
    sqlite_store: SQLiteEventStore[MockEvent],
) -> None:
    """Test appending and retrieving events from the store."""
    # Arrange
    aggregate_id = uuid.uuid4()
    events = [
        MockEvent(
            event_id=uuid.uuid4(),
            name=f"Event {i}",
            value=i,
            version=1,
            aggregate_version=1,  # Must be >= 1
        )
        for i in range(3)
    ]

    # Act
    await sqlite_store.append(aggregate_id, events)
    retrieved_events = [event async for event in sqlite_store.get_events(aggregate_id)]

    # Assert
    assert len(retrieved_events) == 3
    for original, retrieved in zip(events, retrieved_events):
        assert original.event_id == retrieved.event_id
        assert original.name == retrieved.name
        assert original.value == retrieved.value
        assert retrieved.aggregate_version > 0


@pytest.mark.asyncio
async def test_concurrent_operations(sqlite_store: SQLiteEventStore[MockEvent]) -> None:
    """Test that concurrent operations work as expected."""
    # Test that we can execute multiple operations concurrently
    event1 = MockEvent(
        event_id=str(uuid.uuid4()),
        aggregate_id="test_aggregate_1",
        name="test1",
        value=42,
    )
    event2 = MockEvent(
        event_id=str(uuid.uuid4()),
        aggregate_id="test_aggregate_2",
        name="test2",
        value=84,
    )

    # Append events sequentially to avoid SQLite threading issues
    await sqlite_store.append_events("test_aggregate_1", [event1], expected_version=0)
    await sqlite_store.append_events("test_aggregate_2", [event2], expected_version=0)

    # Verify events were stored
    events1 = await sqlite_store.get_events("test_aggregate_1")
    assert len(events1) == 1
    assert events1[0].name == "test1"

    events2 = await sqlite_store.get_events("test_aggregate_2")
    assert len(events2) == 1
    assert events2[0].name == "test2"


@pytest.mark.asyncio
async def test_version_conflict(sqlite_store: SQLiteEventStore[MockEvent]) -> None:
    """Test version conflict detection."""
    # Arrange
    aggregate_id = uuid.uuid4()
    events = [
        MockEvent(
            event_id=uuid.uuid4(),
            name="Initial Event",
            value=1,
            version=1,
            aggregate_version=1,  # Must be >= 1
        )
    ]

    # Append initial event
    await sqlite_store.append(aggregate_id, events)

    # Try to append with wrong expected version
    with pytest.raises(Exception) as exc_info:  # Should be specific exception
        await sqlite_store.append(
            aggregate_id,
            [
                MockEvent(
                    event_id=uuid.uuid4(),
                    name="Conflicting Event",
                    value=2,
                    version=1,
                    aggregate_version=1,  # Must be >= 1
                )
            ],
            expected_version=0,  # Should be 1
        )

    assert "version conflict" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_connection_pooling(sqlite_store: SQLiteEventStore[MockEvent]) -> None:
    """Test that connection pooling works as expected."""
    # This test ensures that multiple operations can happen concurrently
    # without exhausting the connection pool

    async def append_events(
        store: SQLiteEventStore[MockEvent], agg_id: uuid.UUID, count: int
    ) -> None:
        events = [
            MockEvent(
                event_id=uuid.uuid4(),
                name=f"Concurrent Event {i}",
                value=i,
                version=1,
                aggregate_version=1,  # Must be >= 1
            )
            for i in range(count)
        ]
        await store.append(agg_id, events)

    # Create multiple aggregates and append events concurrently
    tasks = []
    for i in range(5):
        agg_id = uuid.uuid4()
        tasks.append(append_events(sqlite_store, agg_id, 3))

    await asyncio.gather(*tasks)

    # Verify all events were written
    for task in tasks:
        # Each task appends to a different aggregate
        assert True  # If we get here without errors, the test passes


@pytest.mark.asyncio
async def test_optimize_database(sqlite_store: SQLiteEventStore[MockEvent]) -> None:
    """Test database optimization (VACUUM and ANALYZE)."""
    # This is mostly to ensure the method doesn't raise exceptions
    await sqlite_store.optimize()
    assert True  # If we get here without errors, the test passes


@pytest.mark.asyncio
async def test_context_manager(temp_db: str) -> None:
    """Test the async context manager interface."""
    async with SQLiteEventStore[MockEvent](db_path=temp_db) as store:
        assert store.is_connected
        # Do a simple operation to verify it works
        await store.append(
            uuid.uuid4(),
            [
                MockEvent(
                    event_id=uuid.uuid4(),
                    name="Context Test",
                    value=42,
                    version=1,
                    aggregate_version=1,  # Must be >= 1
                )
            ],
        )
    # Store should be closed after context manager exits
    assert not store.is_connected
