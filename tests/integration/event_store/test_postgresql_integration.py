"""Integration tests for PostgreSQL event store with actual database."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from uuid import UUID, uuid4

import asyncpg
import pytest
from pydantic import BaseModel, Field

from uno.domain.events import DomainEvent
from uno.persistence.event_store import PostgreSQLEventStore
from uno.event_store.errors import EventStoreVersionConflict, EventStoreError
from uno.injection import Container
from uno.logging import get_logger

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Test database configuration
TEST_DB = os.environ.get("TEST_POSTGRES_DB", "uno_test")
TEST_USER = os.environ.get("TEST_POSTGRES_USER", "postgres")
TEST_PASSWORD = os.environ.get("TEST_POSTGRES_PASSWORD", "postgres")
TEST_HOST = os.environ.get("TEST_POSTGRES_HOST", "localhost")
TEST_PORT = int(os.environ.get("TEST_POSTGRES_PORT", 5432))


# Test event class
class MockEvent(DomainEvent):
    """Test event for integration testing."""

    value: str
    number: int

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


@pytest.fixture(scope="module")
def event_loop():
    """Create an instance of the default event loop for the test module."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def test_db():
    """Set up and tear down a test database."""
    # Connect to the default postgres database to create our test database
    sys_conn = await asyncpg.connect(
        user=TEST_USER,
        password=TEST_PASSWORD,
        host=TEST_HOST,
        port=TEST_PORT,
        database="postgres",
    )

    # Drop the test database if it exists
    await sys_conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB}")

    # Create a fresh test database
    await sys_conn.execute(f"CREATE DATABASE {TEST_DB}")
    await sys_conn.close()

    # Connect to the test database
    conn = await asyncpg.connect(
        user=TEST_USER,
        password=TEST_PASSWORD,
        host=TEST_HOST,
        port=TEST_PORT,
        database=TEST_DB,
    )

    # Enable pgvector extension
    await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

    yield conn

    # Clean up
    await conn.close()

    # Drop the test database
    sys_conn = await asyncpg.connect(
        user=TEST_USER,
        password=TEST_PASSWORD,
        host=TEST_HOST,
        port=TEST_PORT,
        database="postgres",
    )
    await sys_conn.execute(f"DROP DATABASE {TEST_DB}")
    await sys_conn.close()


@pytest.fixture
async def event_store(test_db):
    """Create and initialize an event store for testing."""
    # Create tables
    await test_db.execute(
        """
    CREATE TABLE IF NOT EXISTS events (
        id BIGSERIAL PRIMARY KEY,
        aggregate_id UUID NOT NULL,
        event_id UUID NOT NULL,
        event_type TEXT NOT NULL,
        data JSONB NOT NULL,
        metadata JSONB NOT NULL,
        version INTEGER NOT NULL,
        timestamp TIMESTAMPTZ NOT NULL,
        embedding VECTOR(384),
        UNIQUE(aggregate_id, version)
    )
    """
    )

    # Create indexes
    await test_db.execute(
        """
    CREATE INDEX IF NOT EXISTS idx_events_aggregate_id ON events(aggregate_id);
    CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);
    CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
    """
    )

    # Create event store instance
    container = Container()
    store = PostgreSQLEventStore[MockEvent](
        container=container,
        settings=None,  # Will use defaults from environment
        logger=get_logger("uno.event_store.test"),
    )

    # Override the pool with our test connection
    store._pool = await asyncpg.create_pool(
        user=TEST_USER,
        password=TEST_PASSWORD,
        host=TEST_HOST,
        port=TEST_PORT,
        database=TEST_DB,
        min_size=1,
        max_size=5,
    )

    # Initialize the store
    await store.connect()

    yield store

    # Clean up
    await store.disconnect()


@pytest.mark.asyncio
async def test_event_store_lifecycle(event_store):
    """Test the basic lifecycle of the event store."""
    aggregate_id = uuid4()
    event = MockEvent(
        event_id=uuid4(),
        event_type="test_event",
        timestamp=datetime.now(timezone.utc),
        version=1,
        value="test",
        number=42,
    )

    # Append an event
    await event_store.append(
        aggregate_id=str(aggregate_id),
        events=[event],
    )

    # Retrieve the event
    events = await event_store.get_events(aggregate_id=str(aggregate_id))

    # Verify
    assert len(events) == 1
    assert events[0].event_id == event.event_id
    assert events[0].value == "test"
    assert events[0].number == 42


@pytest.mark.asyncio
async def test_concurrent_writes(event_store):
    """Test that concurrent writes are handled correctly."""
    aggregate_id = uuid4()
    event1 = MockEvent(
        event_id=uuid4(),
        event_type="test_event",
        timestamp=datetime.now(timezone.utc),
        version=1,
        value="first",
        number=1,
    )
    event2 = MockEvent(
        event_id=uuid4(),
        event_type="test_event",
        timestamp=datetime.now(timezone.utc),
        version=2,
        value="second",
        number=2,
    )

    # Append events in parallel
    await asyncio.gather(
        event_store.append(str(aggregate_id), [event1]),
        event_store.append(str(aggregate_id), [event2], expected_version=1),
    )

    # Retrieve the events
    events = await event_store.get_events(str(aggregate_id))

    # Verify both events were stored
    assert len(events) == 2
    assert {e.value for e in events} == {"first", "second"}


@pytest.mark.asyncio
async def test_version_conflict(event_store):
    """Test that version conflicts are detected."""
    aggregate_id = uuid4()
    event1 = MockEvent(
        event_id=uuid4(),
        event_type="test_event",
        timestamp=datetime.now(timezone.utc),
        version=1,
        value="first",
        number=1,
    )
    event2 = MockEvent(
        event_id=uuid4(),
        event_type="test_event",
        timestamp=datetime.now(timezone.utc),
        version=1,  # Same version as event1
        value="second",
        number=2,
    )

    # First append should succeed
    await event_store.append(str(aggregate_id), [event1])

    # Second append with same version should fail
    with pytest.raises(EventStoreVersionConflict):
        await event_store.append(str(aggregate_id), [event2])


@pytest.mark.asyncio
async def test_vector_search(event_store, test_db):
    """Test vector similarity search."""
    if not event_store._vector_extension_available:
        pytest.skip("pgvector extension not available")

    # Create test events with embeddings
    events = [
        MockEvent(
            event_id=uuid4(),
            event_type="test_event",
            timestamp=datetime.now(timezone.utc),
            version=i + 1,
            value=f"event_{i}",
            number=i,
        )
        for i in range(5)
    ]

    # Add events with embeddings
    for i, event in enumerate(events):
        embedding = [0.0] * 384
        embedding[i] = 1.0  # Each event has a unique dimension set to 1.0

        await test_db.execute(
            """
            INSERT INTO events 
            (aggregate_id, event_id, event_type, data, metadata, version, timestamp, embedding)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            str(uuid4()),
            str(event.event_id),
            event.event_type,
            event.model_dump(),
            {},
            event.version,
            event.timestamp,
            embedding,
        )

    # Search for an event similar to the first one
    query_embedding = [0.0] * 384
    query_embedding[0] = 0.9  # Similar to first event

    # This is a placeholder - the actual implementation would need to be updated
    # to support this search interface
    with pytest.raises(NotImplementedError):
        await event_store.search_events_by_vector(
            query_embedding=query_embedding,
            limit=1,
        )
