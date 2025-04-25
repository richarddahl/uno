"""
Integration tests for the event sourcing snapshot functionality.

These tests verify that the snapshot system properly persists and retrieves
aggregate state, using different storage backends and snapshot strategies.
"""

import json
import os
import pytest
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Protocol

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from uno.core.domain.core import AggregateRoot
from uno.core.domain.event_sourced_repository import EventSourcedRepository
from uno.core.errors.result import Result
from uno.core.events.events import DomainEvent
from uno.core.events.event_store import InMemoryEventStore
from uno.core.events.snapshots import (
    CompositeSnapshotStrategy,
    EventCountSnapshotStrategy,
    FileSystemSnapshotStore,
    InMemorySnapshotStore,
    PostgresSnapshotStore,
    TimeBasedSnapshotStrategy,
)
from uno.core.logging.logger import LoggerService


# Test fixtures and helper classes

class TestAggregate(AggregateRoot):
    """Simple aggregate for testing."""
    
    def __init__(self, id: Optional[str] = None, name: str = "", counter: int = 0):
        """Initialize with optional ID and test data."""
        super().__init__(id or str(uuid.uuid4()))
        self.name = name
        self.counter = counter
    
    def change_name(self, name: str) -> None:
        """Change the name and record the event."""
        self.apply_event(DomainEvent(
            event_type="name_changed",
            aggregate_id=str(self.id),
            aggregate_type=self.__class__.__name__,
            data={"name": name}
        ))
    
    def increment_counter(self, amount: int = 1) -> None:
        """Increment the counter and record the event."""
        self.apply_event(DomainEvent(
            event_type="counter_incremented",
            aggregate_id=str(self.id),
            aggregate_type=self.__class__.__name__,
            data={"amount": amount}
        ))
    
    def apply_name_changed(self, event: DomainEvent) -> None:
        """Apply a name change event."""
        self.name = event.data.get("name", self.name)
    
    def apply_counter_incremented(self, event: DomainEvent) -> None:
        """Apply a counter increment event."""
        self.counter += event.data.get("amount", 1)
    
    def to_dict(self) -> dict:
        """Serialize the aggregate to a dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "counter": self.counter
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TestAggregate":
        """Create an aggregate from a dictionary."""
        return cls(
            id=data.get("id"),
            name=data.get("name", ""),
            counter=data.get("counter", 0)
        )


@pytest.fixture
def logger():
    """Provide a logger service for testing."""
    return LoggerService()


@pytest.fixture
def in_memory_event_store(logger):
    """Create an in-memory event store for testing."""
    return InMemoryEventStore(DomainEvent, logger)


@pytest.fixture
def temp_snapshot_dir(tmp_path):
    """Create a temporary directory for snapshots."""
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    yield str(snapshot_dir)
    # Clean up happens automatically with pytest's tmp_path


@pytest.fixture
async def pg_session_factory(request):
    """Create a PostgreSQL session factory for testing."""
    # Check if we should skip PostgreSQL tests
    if not os.environ.get("TEST_PG_URI"):
        pytest.skip("TEST_PG_URI environment variable not set")
        
    # Create engine and session factory
    engine = create_async_engine(os.environ["TEST_PG_URI"])
    async_session_factory = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            aggregate_id VARCHAR(255) PRIMARY KEY,
            aggregate_type VARCHAR(255) NOT NULL,
            created_at TIMESTAMP NOT NULL,
            data JSONB NOT NULL
        )
        """)
    
    yield async_session_factory
    
    # Clean up
    async with engine.begin() as conn:
        await conn.execute("DROP TABLE IF EXISTS snapshots")
    
    await engine.dispose()


# Tests for different snapshot stores

@pytest.mark.asyncio
async def test_in_memory_snapshot_store(logger, in_memory_event_store):
    """Test the in-memory snapshot store."""
    # Set up
    snapshot_store = InMemorySnapshotStore(logger)
    snapshot_strategy = EventCountSnapshotStrategy(threshold=1)
    
    repository = EventSourcedRepository(
        aggregate_type=TestAggregate,
        event_store=in_memory_event_store, 
        logger=logger,
        snapshot_store=snapshot_store,
        snapshot_strategy=snapshot_strategy
    )
    
    # Create and save an aggregate
    aggregate = TestAggregate(name="Test", counter=0)
    aggregate.change_name("Updated Name")
    result = await repository.save(aggregate)
    assert result.is_success
    
    # Clear the in-memory cache to force loading from the snapshot store
    repository._snapshots = {}
    
    # Load the aggregate
    result = await repository.get_by_id(str(aggregate.id))
    assert result.is_success
    assert result.value is not None
    assert result.value.name == "Updated Name"
    assert result.value.counter == 0
    
    # Update and save again
    aggregate = result.value
    aggregate.increment_counter(5)
    result = await repository.save(aggregate)
    assert result.is_success
    
    # Clear cache again
    repository._snapshots = {}
    
    # Verify updates are correctly restored from snapshot
    result = await repository.get_by_id(str(aggregate.id))
    assert result.is_success
    assert result.value is not None
    assert result.value.name == "Updated Name"
    assert result.value.counter == 5


@pytest.mark.asyncio
async def test_file_system_snapshot_store(logger, in_memory_event_store, temp_snapshot_dir):
    """Test the file system snapshot store."""
    # Set up
    snapshot_store = FileSystemSnapshotStore(logger, temp_snapshot_dir)
    snapshot_strategy = EventCountSnapshotStrategy(threshold=1)
    
    repository = EventSourcedRepository(
        aggregate_type=TestAggregate,
        event_store=in_memory_event_store, 
        logger=logger,
        snapshot_store=snapshot_store,
        snapshot_strategy=snapshot_strategy
    )
    
    # Create and save an aggregate
    aggregate = TestAggregate(name="Test", counter=0)
    aggregate.change_name("Updated Name")
    result = await repository.save(aggregate)
    assert result.is_success
    
    # Verify the snapshot file exists
    snapshot_path = Path(temp_snapshot_dir) / f"{aggregate.id}.json"
    assert snapshot_path.exists()
    
    # Verify file contents
    with open(snapshot_path) as f:
        data = json.load(f)
        assert data["name"] == "Updated Name"
        assert data["counter"] == 0
        assert data["_type"] == "TestAggregate"
    
    # Clear the in-memory cache to force loading from the snapshot store
    repository._snapshots = {}
    
    # Load the aggregate
    result = await repository.get_by_id(str(aggregate.id))
    assert result.is_success
    assert result.value is not None
    assert result.value.name == "Updated Name"
    assert result.value.counter == 0


@pytest.mark.asyncio
async def test_postgres_snapshot_store(logger, in_memory_event_store, pg_session_factory):
    """Test the PostgreSQL snapshot store."""
    # Set up
    snapshot_store = PostgresSnapshotStore(logger, pg_session_factory)
    snapshot_strategy = EventCountSnapshotStrategy(threshold=1)
    
    repository = EventSourcedRepository(
        aggregate_type=TestAggregate,
        event_store=in_memory_event_store, 
        logger=logger,
        snapshot_store=snapshot_store,
        snapshot_strategy=snapshot_strategy
    )
    
    # Create and save an aggregate
    aggregate = TestAggregate(name="Test", counter=0)
    aggregate.change_name("Updated Name")
    result = await repository.save(aggregate)
    assert result.is_success
    
    # Clear the in-memory cache to force loading from the snapshot store
    repository._snapshots = {}
    
    # Load the aggregate
    result = await repository.get_by_id(str(aggregate.id))
    assert result.is_success
    assert result.value is not None
    assert result.value.name == "Updated Name"
    assert result.value.counter == 0


# Tests for snapshot strategies

@pytest.mark.asyncio
async def test_event_count_snapshot_strategy(logger, in_memory_event_store):
    """Test the event count snapshot strategy."""
    # Set up with a threshold of 2 events
    snapshot_store = InMemorySnapshotStore(logger)
    snapshot_strategy = EventCountSnapshotStrategy(threshold=2)
    
    repository = EventSourcedRepository(
        aggregate_type=TestAggregate,
        event_store=in_memory_event_store, 
        logger=logger,
        snapshot_store=snapshot_store,
        snapshot_strategy=snapshot_strategy
    )
    
    # Create aggregate with 1 event - shouldn't trigger snapshot
    aggregate = TestAggregate(name="Test", counter=0)
    aggregate.change_name("Updated Name")
    await repository.save(aggregate)
    
    # Verify the snapshot store wasn't called (no direct way to check, so we'll test indirectly)
    result = await snapshot_store.get_snapshot(str(aggregate.id), TestAggregate)
    assert result.is_success
    assert result.value is None  # No snapshot should exist yet
    
    # Add another event - should trigger snapshot
    aggregate.increment_counter(1)
    await repository.save(aggregate)
    
    # Verify the snapshot was created
    result = await snapshot_store.get_snapshot(str(aggregate.id), TestAggregate)
    assert result.is_success
    assert result.value is not None
    assert result.value.name == "Updated Name"
    assert result.value.counter == 1


@pytest.mark.asyncio
async def test_composite_snapshot_strategy(logger, in_memory_event_store):
    """Test the composite snapshot strategy."""
    # Set up with two strategies that won't trigger individually
    event_strategy = EventCountSnapshotStrategy(threshold=3)  # Won't trigger with 1 event
    time_strategy = TimeBasedSnapshotStrategy(minutes_threshold=60)  # Won't trigger immediately
    
    # Create a mock strategy that will always trigger
    class AlwaysSnapshotStrategy:
        async def should_snapshot(self, aggregate_id: str, event_count: int) -> bool:
            return True
    
    # Composite strategy with one that always triggers
    composite_strategy = CompositeSnapshotStrategy([
        event_strategy,
        time_strategy,
        AlwaysSnapshotStrategy()
    ])
    
    snapshot_store = InMemorySnapshotStore(logger)
    repository = EventSourcedRepository(
        aggregate_type=TestAggregate,
        event_store=in_memory_event_store,
        logger=logger,
        snapshot_store=snapshot_store,
        snapshot_strategy=composite_strategy
    )
    
    # Create and save an aggregate - should trigger snapshot due to AlwaysSnapshotStrategy
    aggregate = TestAggregate(name="Test", counter=0)
    aggregate.change_name("Composite Test")
    await repository.save(aggregate)
    
    # Verify snapshot was created
    result = await snapshot_store.get_snapshot(str(aggregate.id), TestAggregate)
    assert result.is_success
    assert result.value is not None
    assert result.value.name == "Composite Test"


# Edge case and recovery tests

@pytest.mark.asyncio
async def test_rebuild_from_events_after_snapshot(logger, in_memory_event_store):
    """Test rebuilding from events when a snapshot exists but more events were added after."""
    snapshot_store = InMemorySnapshotStore(logger)
    snapshot_strategy = EventCountSnapshotStrategy(threshold=1)
    
    repository = EventSourcedRepository(
        aggregate_type=TestAggregate,
        event_store=in_memory_event_store,
        logger=logger,
        snapshot_store=snapshot_store,
        snapshot_strategy=snapshot_strategy
    )
    
    # Create and save an aggregate with initial state
    aggregate = TestAggregate(name="Initial", counter=0)
    await repository.save(aggregate)
    
    # Now update the aggregate but manipulate the event store directly
    # so the snapshot doesn't get updated
    event = DomainEvent(
        event_type="counter_incremented",
        aggregate_id=str(aggregate.id),
        aggregate_type=TestAggregate.__name__,
        data={"amount": 10}
    )
    await in_memory_event_store.save_event(event)
    
    # Load the aggregate - it should include both the snapshot and the new event
    result = await repository.get_by_id(str(aggregate.id))
    assert result.is_success
    assert result.value is not None
    assert result.value.name == "Initial"  # From snapshot
    assert result.value.counter == 10  # From the event added after snapshot


@pytest.mark.asyncio
async def test_snapshot_failure_handling(logger, in_memory_event_store):
    """Test that the system continues to work even if snapshot creation fails."""
    # Create a failing snapshot store
    class FailingSnapshotStore(InMemorySnapshotStore):
        async def save_snapshot(self, aggregate: AggregateRoot) -> Result[None, Exception]:
            return Result.failure(Exception("Simulated snapshot failure"))
    
    snapshot_store = FailingSnapshotStore(logger)
    snapshot_strategy = EventCountSnapshotStrategy(threshold=1)
    
    repository = EventSourcedRepository(
        aggregate_type=TestAggregate,
        event_store=in_memory_event_store,
        logger=logger,
        snapshot_store=snapshot_store,
        snapshot_strategy=snapshot_strategy
    )
    
    # Create and save an aggregate - snapshot will fail but overall save should succeed
    aggregate = TestAggregate(name="Test", counter=0)
    aggregate.change_name("Updated Name")
    result = await repository.save(aggregate)
    
    # Verify save still succeeded
    assert result.is_success
    
    # Verify we can still retrieve the aggregate using events
    result = await repository.get_by_id(str(aggregate.id))
    assert result.is_success
    assert result.value is not None
    assert result.value.name == "Updated Name"
