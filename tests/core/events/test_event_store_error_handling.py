"""
Integration tests for the event sourcing error handling.

These tests verify that the event store properly handles errors using the Result monad pattern.
"""

import os
import pytest
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from uno.core.domain.core import AggregateRoot
from uno.core.domain.event_sourced_repository import EventSourcedRepository
from uno.core.errors.result import Failure, Result, Success
from uno.core.events.events import DomainEvent
from uno.core.events.event_store import InMemoryEventStore
from uno.core.events.postgres_event_store import PostgresEventStore
from uno.core.logging.logger import LoggerService


# Test fixtures and helper classes

class TestAggregate(AggregateRoot):
    """Simple aggregate for testing."""
    
    def __init__(self, id: str | None = None, name: str = "", value: int = 0):
        """Initialize with optional ID and test data."""
        super().__init__(id or str(uuid.uuid4()))
        self.name = name
        self.value = value
    
    def update_name(self, name: str) -> None:
        """Update the name and record an event."""
        self.apply_event(DomainEvent(
            event_type="name_updated",
            aggregate_id=str(self.id),
            aggregate_type=self.__class__.__name__,
            data={"name": name}
        ))
    
    def update_value(self, value: int) -> None:
        """Update the value and record an event."""
        self.apply_event(DomainEvent(
            event_type="value_updated",
            aggregate_id=str(self.id),
            aggregate_type=self.__class__.__name__,
            data={"value": value}
        ))
    
    def apply_name_updated(self, event: DomainEvent) -> None:
        """Apply a name update event."""
        self.name = event.data.get("name", self.name)
    
    def apply_value_updated(self, event: DomainEvent) -> None:
        """Apply a value update event."""
        self.value = event.data.get("value", self.value)
    
    def to_dict(self) -> dict:
        """Serialize the aggregate to a dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "value": self.value
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TestAggregate":
        """Create an aggregate from a dictionary."""
        return cls(
            id=data.get("id"),
            name=data.get("name", ""),
            value=data.get("value", 0)
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
        CREATE TABLE IF NOT EXISTS domain_events (
            id SERIAL PRIMARY KEY,
            event_type VARCHAR(255) NOT NULL,
            aggregate_id VARCHAR(255),
            aggregate_type VARCHAR(255),
            event_data JSONB NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_domain_events_aggregate_id ON domain_events(aggregate_id);
        CREATE INDEX IF NOT EXISTS idx_domain_events_event_type ON domain_events(event_type);
        """)
    
    yield async_session_factory
    
    # Clean up
    async with engine.begin() as conn:
        await conn.execute("DROP TABLE IF EXISTS domain_events")
    
    await engine.dispose()


# Mock failing event stores for testing error handling

class FailingEventStore(InMemoryEventStore):
    """Event store that fails on specific operations for testing error handling."""
    
    def __init__(self, event_type, logger, fail_on=None):
        """
        Initialize with a set of operations to fail on.
        
        Args:
            event_type: The type of events to store
            logger: Logger service
            fail_on: List of method names that should fail
        """
        super().__init__(event_type, logger)
        self.fail_on = fail_on or set()
    
    async def save_event(self, event: DomainEvent) -> Result[DomainEvent, Exception]:
        """Save a domain event, failing if configured to do so."""
        if "save_event" in self.fail_on:
            return Failure(Exception("Simulated save_event failure"))
        return await super().save_event(event)
    
    async def get_events(
        self,
        aggregate_id: str | None = None,
        event_type: str | None = None,
        limit: int | None = None
    ) -> Result[list[DomainEvent], Exception]:
        """Get events, failing if configured to do so."""
        if "get_events" in self.fail_on:
            return Failure(Exception("Simulated get_events failure"))
        return await super().get_events(aggregate_id, event_type, limit)


# Tests for error handling in EventSourcedRepository

@pytest.mark.asyncio
async def test_save_success(logger, in_memory_event_store):
    """Test successful save operation with Result monad."""
    repository = EventSourcedRepository(
        aggregate_type=TestAggregate,
        event_store=in_memory_event_store,
        logger=logger
    )
    
    # Create and save an aggregate
    aggregate = TestAggregate(name="Test", value=42)
    aggregate.update_name("Updated Name")
    
    result = await repository.save(aggregate)
    
    # Verify result is a Success
    assert result.is_success
    assert not result.is_failure
    assert result.value is aggregate  # The returned value should be the same aggregate


@pytest.mark.asyncio
async def test_save_failure(logger):
    """Test failing save operation with Result monad."""
    # Create event store that fails on save_event
    failing_store = FailingEventStore(DomainEvent, logger, fail_on={"save_event"})
    
    repository = EventSourcedRepository(
        aggregate_type=TestAggregate,
        event_store=failing_store,
        logger=logger
    )
    
    # Create and try to save an aggregate
    aggregate = TestAggregate(name="Test", value=42)
    aggregate.update_name("Updated Name")
    
    result = await repository.save(aggregate)
    
    # Verify result is a Failure
    assert result.is_failure
    assert not result.is_success
    assert str(result.error) == "Simulated save_event failure"


@pytest.mark.asyncio
async def test_get_by_id_success(logger, in_memory_event_store):
    """Test successful get_by_id operation with Result monad."""
    repository = EventSourcedRepository(
        aggregate_type=TestAggregate,
        event_store=in_memory_event_store,
        logger=logger
    )
    
    # Create and save an aggregate
    aggregate = TestAggregate(name="Test", value=42)
    aggregate.update_name("Updated Name")
    save_result = await repository.save(aggregate)
    assert save_result.is_success
    
    # Get the aggregate by ID
    result = await repository.get_by_id(str(aggregate.id))
    
    # Verify result is a Success
    assert result.is_success
    assert not result.is_failure
    assert result.value is not None
    assert result.value.name == "Updated Name"
    assert result.value.value == 42


@pytest.mark.asyncio
async def test_get_by_id_not_found(logger, in_memory_event_store):
    """Test get_by_id with non-existent ID returns Success with None."""
    repository = EventSourcedRepository(
        aggregate_type=TestAggregate,
        event_store=in_memory_event_store,
        logger=logger
    )
    
    # Get an aggregate that doesn't exist
    non_existent_id = str(uuid.uuid4())
    result = await repository.get_by_id(non_existent_id)
    
    # Verify result is a Success but with None value
    assert result.is_success
    assert not result.is_failure
    assert result.value is None


@pytest.mark.asyncio
async def test_get_by_id_failure(logger):
    """Test failing get_by_id operation with Result monad."""
    # Create event store that fails on get_events
    failing_store = FailingEventStore(DomainEvent, logger, fail_on={"get_events"})
    
    repository = EventSourcedRepository(
        aggregate_type=TestAggregate,
        event_store=failing_store,
        logger=logger
    )
    
    # Try to get an aggregate by ID
    result = await repository.get_by_id(str(uuid.uuid4()))
    
    # Verify result is a Failure
    assert result.is_failure
    assert not result.is_success
    assert str(result.error) == "Simulated get_events failure"


@pytest.mark.asyncio
async def test_list_success(logger, in_memory_event_store):
    """Test successful list operation with Result monad."""
    repository = EventSourcedRepository(
        aggregate_type=TestAggregate,
        event_store=in_memory_event_store,
        logger=logger
    )
    
    # Create and save multiple aggregates
    aggregates = []
    for i in range(3):
        aggregate = TestAggregate(name=f"Aggregate {i}", value=i * 10)
        aggregate.update_value(i * 10 + 5)  # Create an event
        save_result = await repository.save(aggregate)
        assert save_result.is_success
        aggregates.append(aggregate)
    
    # List all aggregates
    result = await repository.list()
    
    # Verify result is a Success
    assert result.is_success
    assert not result.is_failure
    assert len(result.value) == 3
    
    # Check that aggregates are correctly restored
    ids = [a.id for a in result.value]
    for original in aggregates:
        assert str(original.id) in ids


@pytest.mark.asyncio
async def test_list_failure(logger):
    """Test failing list operation with Result monad."""
    # Create event store that fails on get_events
    failing_store = FailingEventStore(DomainEvent, logger, fail_on={"get_events"})
    
    repository = EventSourcedRepository(
        aggregate_type=TestAggregate,
        event_store=failing_store,
        logger=logger
    )
    
    # Try to list aggregates
    result = await repository.list()
    
    # Verify result is a Failure
    assert result.is_failure
    assert not result.is_success
    assert str(result.error) == "Simulated get_events failure"


@pytest.mark.asyncio
async def test_exists_success(logger, in_memory_event_store):
    """Test successful exists operation with Result monad."""
    repository = EventSourcedRepository(
        aggregate_type=TestAggregate,
        event_store=in_memory_event_store,
        logger=logger
    )
    
    # Create and save an aggregate
    aggregate = TestAggregate(name="Test Exists", value=100)
    aggregate.update_name("Updated Name")  # Create an event
    save_result = await repository.save(aggregate)
    assert save_result.is_success
    
    # Check if aggregate exists
    result = await repository.exists(str(aggregate.id))
    
    # Verify result is a Success with True
    assert result.is_success
    assert not result.is_failure
    assert result.value is True
    
    # Check for non-existent aggregate
    non_existent_id = str(uuid.uuid4())
    result = await repository.exists(non_existent_id)
    
    # Verify result is a Success with False
    assert result.is_success
    assert not result.is_failure
    assert result.value is False


@pytest.mark.asyncio
async def test_exists_failure(logger):
    """Test failing exists operation with Result monad."""
    # Create event store that fails on get_events
    failing_store = FailingEventStore(DomainEvent, logger, fail_on={"get_events"})
    
    repository = EventSourcedRepository(
        aggregate_type=TestAggregate,
        event_store=failing_store,
        logger=logger
    )
    
    # Try to check if an aggregate exists
    result = await repository.exists(str(uuid.uuid4()))
    
    # Verify result is a Failure
    assert result.is_failure
    assert not result.is_success
    assert str(result.error) == "Simulated get_events failure"


@pytest.mark.asyncio
async def test_remove_success(logger, in_memory_event_store):
    """Test successful remove operation with Result monad."""
    repository = EventSourcedRepository(
        aggregate_type=TestAggregate,
        event_store=in_memory_event_store,
        logger=logger
    )
    
    # Create and save an aggregate
    aggregate = TestAggregate(name="Test Remove", value=200)
    aggregate.update_name("Updated Name")  # Create an event
    save_result = await repository.save(aggregate)
    assert save_result.is_success
    
    # Remove the aggregate
    remove_result = await repository.remove(aggregate)
    
    # Verify result is a Success
    assert remove_result.is_success
    assert not remove_result.is_failure
    
    # Verify the aggregate is indeed removed
    exists_result = await repository.exists(str(aggregate.id))
    assert exists_result.is_success
    assert exists_result.value is True  # Still exists but has a delete event
    
    # Try to get the aggregate - it might have a delete marker
    get_result = await repository.get_by_id(str(aggregate.id))
    assert get_result.is_success
    
    # The last event should be an aggregate_deleted event
    events_result = await in_memory_event_store.get_events(aggregate_id=str(aggregate.id))
    assert events_result.is_success
    last_event = events_result.value[-1]
    assert last_event.event_type == "aggregate_deleted"


@pytest.mark.asyncio
async def test_remove_failure(logger):
    """Test failing remove operation with Result monad."""
    # Create event store that fails on save_event (for the deletion event)
    failing_store = FailingEventStore(DomainEvent, logger, fail_on={"save_event"})
    
    repository = EventSourcedRepository(
        aggregate_type=TestAggregate,
        event_store=failing_store,
        logger=logger
    )
    
    # Create an aggregate (not saved, but that's OK for this test)
    aggregate = TestAggregate(name="Test Remove Failure", value=300)
    
    # Try to remove the aggregate
    result = await repository.remove(aggregate)
    
    # Verify result is a Failure
    assert result.is_failure
    assert not result.is_success
    assert str(result.error) == "Simulated save_event failure"


# Integration tests with PostgreSQL

@pytest.mark.asyncio
async def test_postgres_event_store_integration(logger, pg_session_factory):
    """Integration test using PostgreSQL event store with Result monads."""
    # Skip if no PostgreSQL connection
    if not os.environ.get("TEST_PG_URI"):
        pytest.skip("TEST_PG_URI environment variable not set")
    
    # Set up PostgreSQL event store
    event_store = PostgresEventStore(
        event_type=DomainEvent,
        logger=logger,
        db_session_factory=pg_session_factory
    )
    
    repository = EventSourcedRepository(
        aggregate_type=TestAggregate,
        event_store=event_store,
        logger=logger
    )
    
    # Create and save an aggregate
    aggregate = TestAggregate(name="PostgreSQL Test", value=500)
    aggregate.update_name("Updated in PostgreSQL")
    aggregate.update_value(550)
    
    save_result = await repository.save(aggregate)
    assert save_result.is_success
    
    # Get the aggregate by ID
    result = await repository.get_by_id(str(aggregate.id))
    
    # Verify result is a Success
    assert result.is_success
    assert result.value is not None
    assert result.value.name == "Updated in PostgreSQL"
    assert result.value.value == 550
    
    # Test the exists method
    exists_result = await repository.exists(str(aggregate.id))
    assert exists_result.is_success
    assert exists_result.value is True
    
    # Test the list method
    list_result = await repository.list()
    assert list_result.is_success
    assert len(list_result.value) > 0
    found = False
    for a in list_result.value:
        if str(a.id) == str(aggregate.id):
            found = True
            break
    assert found


# Error recovery tests

@pytest.mark.asyncio
async def test_error_recovery_with_aggregate_updates(logger, in_memory_event_store):
    """Test that aggregates remain consistent when errors occur and are resolved."""
    # Create repository with normal event store
    repository = EventSourcedRepository(
        aggregate_type=TestAggregate,
        event_store=in_memory_event_store,
        logger=logger
    )
    
    # Create and save an aggregate
    aggregate = TestAggregate(name="Recovery Test", value=1000)
    aggregate.update_name("Initial Update")
    save_result = await repository.save(aggregate)
    assert save_result.is_success
    
    # Now create a failing repository with the same aggregate ID
    failing_store = FailingEventStore(DomainEvent, logger, fail_on={"save_event"})
    failing_repository = EventSourcedRepository(
        aggregate_type=TestAggregate,
        event_store=failing_store,
        logger=logger
    )
    
    # Get the aggregate using the failing repository
    get_result = await failing_repository.get_by_id(str(aggregate.id))
    assert get_result.is_success
    failing_aggregate = get_result.value
    
    # Try to update and save the aggregate - this should fail
    failing_aggregate.update_value(2000)
    save_result = await failing_repository.save(failing_aggregate)
    assert save_result.is_failure
    
    # Now go back to the working repository
    # The aggregate should still have its original state
    get_result = await repository.get_by_id(str(aggregate.id))
    assert get_result.is_success
    recovered_aggregate = get_result.value
    
    assert recovered_aggregate.name == "Initial Update"
    assert recovered_aggregate.value == 1000  # Not 2000, since that update failed
    
    # Now we can successfully update
    recovered_aggregate.update_value(3000)
    save_result = await repository.save(recovered_aggregate)
    assert save_result.is_success
    
    # Verify the final state
    get_result = await repository.get_by_id(str(aggregate.id))
    assert get_result.is_success
    final_aggregate = get_result.value
    
    assert final_aggregate.name == "Initial Update"
    assert final_aggregate.value == 3000
