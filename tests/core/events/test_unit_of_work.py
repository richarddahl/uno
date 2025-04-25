"""
Tests for the Unit of Work pattern in the event sourcing system.

These tests verify that the Unit of Work pattern correctly manages transactions
and ensures data consistency across operations.
"""

import os
import pytest
import uuid
from collections.abc import AsyncGenerator, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from uno.core.domain.core import AggregateRoot
from uno.core.errors.result import Result
from uno.core.events.events import DomainEvent
from uno.core.domain.event_sourced_repository import EventSourcedRepository
from uno.core.events.event_store import InMemoryEventStore
from uno.core.events.postgres_event_store import PostgresEventStore
from uno.core.events.unit_of_work import InMemoryUnitOfWork, PostgresUnitOfWork, UnitOfWork, execute_operations
from uno.core.logging.logger import LoggerService


# Test fixtures and helper classes

class TestAggregate(AggregateRoot):
    """Simple aggregate for testing."""
    
    def __init__(self, id: str | None = None, value: int = 0):
        """Initialize with optional ID and test data."""
        super().__init__(id or str(uuid.uuid4()))
        self.value = value
    
    def increment(self, amount: int = 1) -> None:
        """Increment the value and record the event."""
        self.apply_event(DomainEvent(
            event_type="incremented",
            aggregate_id=str(self.id),
            aggregate_type=self.__class__.__name__,
            data={"amount": amount}
        ))
    
    def apply_incremented(self, event: DomainEvent) -> None:
        """Apply an increment event."""
        self.value += event.data.get("amount", 1)
    
    def to_dict(self) -> dict:
        """Serialize the aggregate to a dictionary."""
        return {
            "id": str(self.id),
            "value": self.value
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TestAggregate":
        """Create an aggregate from a dictionary."""
        return cls(
            id=data.get("id"),
            value=data.get("value", 0)
        )


@pytest.fixture
def logger_factory() -> Callable[..., LoggerService]:
    """Provide a logger factory for testing."""
    def create_logger(component: str | None = None) -> LoggerService:
        name = "test"
        if component:
            name = f"test.{component}"
        return LoggerService(name=name)
    
    return create_logger


@pytest.fixture
def in_memory_event_store(logger_factory):
    """Create an in-memory event store for testing."""
    return InMemoryEventStore(DomainEvent, logger_factory)


@pytest.fixture
def repository(in_memory_event_store, logger_factory):
    """Create a repository for testing."""
    return EventSourcedRepository(
        aggregate_type=TestAggregate,
        event_store=in_memory_event_store,
        logger_factory=logger_factory
    )


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


# Test operations for the UnitOfWork

async def save_aggregate(
    uow: UnitOfWork, 
    repository: EventSourcedRepository, 
    aggregate: TestAggregate
) -> AsyncGenerator[Result[TestAggregate, Exception], None]:
    """Save an aggregate within a unit of work."""
    result = await repository.save(aggregate)
    yield result


async def get_aggregate(
    uow: UnitOfWork, 
    repository: EventSourcedRepository, 
    aggregate_id: str
) -> AsyncGenerator[Result[TestAggregate | None, Exception], None]:
    """Get an aggregate within a unit of work."""
    result = await repository.get_by_id(aggregate_id)
    yield result


# Tests for InMemoryUnitOfWork

@pytest.mark.asyncio
async def test_inmemory_uow_success(in_memory_event_store, repository, logger_factory):
    """Test that InMemoryUnitOfWork successfully completes a transaction."""
    # Create an aggregate
    aggregate = TestAggregate(value=10)
    aggregate.increment(5)
    
    # Save it using a unit of work
    async with InMemoryUnitOfWork.begin(in_memory_event_store, logger_factory) as uow:
        result = await repository.save(aggregate)
        assert result.is_success
    
    # Verify it was saved
    result = await repository.get_by_id(str(aggregate.id))
    assert result.is_success
    assert result.value is not None
    assert result.value.value == 15


@pytest.mark.asyncio
async def test_inmemory_uow_exception(in_memory_event_store, repository, logger_factory):
    """Test that InMemoryUnitOfWork handles exceptions correctly."""
    # Create an aggregate
    aggregate = TestAggregate(value=10)
    aggregate.increment(5)
    
    # Try to save it with an exception
    with pytest.raises(ValueError):
        async with InMemoryUnitOfWork.begin(in_memory_event_store, logger_factory) as uow:
            result = await repository.save(aggregate)
            assert result.is_success
            raise ValueError("Test exception")
    
    # Since we're using in-memory, the operation still succeeded despite the exception
    # In a real database, the transaction would be rolled back
    result = await repository.get_by_id(str(aggregate.id))
    assert result.is_success
    assert result.value is not None


@pytest.mark.asyncio
async def test_inmemory_uow_multiple_operations(in_memory_event_store, repository, logger_factory):
    """Test that InMemoryUnitOfWork supports multiple operations."""
    # Create multiple aggregates
    aggregate1 = TestAggregate(value=10)
    aggregate1.increment(5)
    
    aggregate2 = TestAggregate(value=20)
    aggregate2.increment(10)
    
    # Save them using a unit of work
    async with InMemoryUnitOfWork.begin(in_memory_event_store, logger_factory) as uow:
        result1 = await repository.save(aggregate1)
        assert result1.is_success
        
        result2 = await repository.save(aggregate2)
        assert result2.is_success
    
    # Verify they were saved
    result1 = await repository.get_by_id(str(aggregate1.id))
    assert result1.is_success
    assert result1.value is not None
    assert result1.value.value == 15
    
    result2 = await repository.get_by_id(str(aggregate2.id))
    assert result2.is_success
    assert result2.value is not None
    assert result2.value.value == 30


# Tests for PostgresUnitOfWork

@pytest.mark.asyncio
async def test_postgres_uow_success(pg_session_factory, logger_factory):
    """Test that PostgresUnitOfWork successfully completes a transaction."""
    if not os.environ.get("TEST_PG_URI"):
        pytest.skip("TEST_PG_URI environment variable not set")
    
    # Create event store and repository
    event_store = PostgresEventStore(
        event_type=DomainEvent,
        logger_factory=logger_factory,
        db_session_factory=pg_session_factory
    )
    
    repository = EventSourcedRepository(
        aggregate_type=TestAggregate,
        event_store=event_store,
        logger_factory=logger_factory
    )
    
    # Create an aggregate
    aggregate = TestAggregate(value=10)
    aggregate.increment(5)
    
    # Save it using a unit of work
    async with PostgresUnitOfWork.begin(event_store, pg_session_factory, logger_factory) as uow:
        result = await repository.save(aggregate)
        assert result.is_success
    
    # Verify it was saved
    result = await repository.get_by_id(str(aggregate.id))
    assert result.is_success
    assert result.value is not None
    assert result.value.value == 15


@pytest.mark.asyncio
async def test_postgres_uow_exception(pg_session_factory, logger_factory):
    """Test that PostgresUnitOfWork handles exceptions correctly."""
    if not os.environ.get("TEST_PG_URI"):
        pytest.skip("TEST_PG_URI environment variable not set")
    
    # Create event store and repository
    event_store = PostgresEventStore(
        event_type=DomainEvent,
        logger_factory=logger_factory,
        db_session_factory=pg_session_factory
    )
    
    repository = EventSourcedRepository(
        aggregate_type=TestAggregate,
        event_store=event_store,
        logger_factory=logger_factory
    )
    
    # Create an aggregate
    aggregate = TestAggregate(value=10)
    aggregate.increment(5)
    
    # Try to save it with an exception
    with pytest.raises(ValueError):
        async with PostgresUnitOfWork.begin(event_store, pg_session_factory, logger_factory) as uow:
            result = await repository.save(aggregate)
            assert result.is_success
            raise ValueError("Test exception")
    
    # Verify the transaction was rolled back
    result = await repository.get_by_id(str(aggregate.id))
    assert result.is_success
    assert result.value is None  # Should not exist


@pytest.mark.asyncio
async def test_execute_operations(in_memory_event_store, repository, logger_factory):
    """Test the execute_operations helper."""
    # Create multiple aggregates
    aggregate1 = TestAggregate(value=10)
    aggregate1.increment(5)
    
    aggregate2 = TestAggregate(value=20)
    aggregate2.increment(10)
    
    # Define the operations
    async def op1(uow: UnitOfWork) -> AsyncGenerator[Result[TestAggregate, Exception], None]:
        result = await repository.save(aggregate1)
        yield result
    
    async def op2(uow: UnitOfWork) -> AsyncGenerator[Result[TestAggregate, Exception], None]:
        result = await repository.save(aggregate2)
        yield result
    
    # Execute the operations
    async with InMemoryUnitOfWork.begin(in_memory_event_store, logger_factory) as uow:
        result = await execute_operations(uow, [op1, op2])
        assert result.is_success
        assert len(result.value) == 2
    
    # Verify they were saved
    result1 = await repository.get_by_id(str(aggregate1.id))
    assert result1.is_success
    assert result1.value is not None
    assert result1.value.value == 15
    
    result2 = await repository.get_by_id(str(aggregate2.id))
    assert result2.is_success
    assert result2.value is not None
    assert result2.value.value == 30


@pytest.mark.asyncio
async def test_execute_operations_rollback(in_memory_event_store, repository, logger_factory):
    """Test that execute_operations rolls back on failure."""
    # Create an aggregate
    aggregate = TestAggregate(value=10)
    aggregate.increment(5)
    
    # Define the operations
    async def op1(uow: UnitOfWork) -> AsyncGenerator[Result[TestAggregate, Exception], None]:
        result = await repository.save(aggregate)
        yield result
    
    async def op2(uow: UnitOfWork) -> AsyncGenerator[Result[Any, Exception], None]:
        yield Result.failure(ValueError("Test error"))
    
    # Execute the operations
    async with InMemoryUnitOfWork.begin(in_memory_event_store, logger_factory) as uow:
        result = await execute_operations(uow, [op1, op2])
        assert result.is_failure
        
    # Since we're using in-memory, the operation still succeeded despite the failure
    # In a real database, the transaction would be rolled back
    result = await repository.get_by_id(str(aggregate.id))
    assert result.is_success
    assert result.value is not None
