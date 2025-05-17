from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, AsyncIterator
from uuid import UUID

import asyncpg
import pytest
from testcontainers.postgres import PostgresContainer

from uno.domain.events import DomainEvent
from uno.event_store.errors import (
    EventStoreConnectError,
    EventStoreTransactionError,
    EventStoreVersionConflict,
    EventStoreAppendError,
    EventStoreGetEventsError,
)
from uno.persistence.event_store.pgvector import PGVectorEventStore


class MockEvent(DomainEvent):
    """Test event class."""

    def __init__(self, test_field: str = "test_value"):
        super().__init__()
        self.test_field = test_field
        self._state = {"test_field": test_field}

    @property
    def state(self) -> dict[str, Any]:
        if not hasattr(self, "_state") or self._state is None:
            self._state = {"test_field": self.test_field}
        return self._state

    @state.setter
    def state(self, value: dict[str, Any]) -> None:
        self._state = value
        if value and "test_field" in value:
            self.test_field = value["test_field"]

    def to_dict(self) -> dict[str, Any]:
        return {
            **super().to_dict(),
            "test_field": self.test_field,
            "state": self.state,
        }


@pytest.fixture(scope="module")
def postgres_container():
    """Start a PostgreSQL container with pgvector extension."""
    with PostgresContainer(
        "pgvector/pgvector:pg16", username="test", password="test", dbname="test"
    ) as container:
        # Wait for container to be ready
        import time

        time.sleep(5)

        # Get the container's connection details
        host = container.get_container_host_ip()
        port = container.get_exposed_port(5432)

        # Create a connection string
        dsn = f"postgresql://test:test@{host}:{port}/test"

        # Initialize database schema
        async def init_db():
            conn = await asyncpg.connect(dsn)
            try:
                # Enable pgvector extension
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

                # Create events table
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS events (
                        event_id UUID PRIMARY KEY,
                        aggregate_id UUID NOT NULL,
                        event_type TEXT NOT NULL,
                        occurred_on TIMESTAMP WITH TIME ZONE NOT NULL,
                        version INTEGER NOT NULL CHECK (version > 0),
                        aggregate_version INTEGER NOT NULL CHECK (aggregate_version > 0),
                        state JSONB NOT NULL,
                        metadata JSONB NOT NULL DEFAULT '{}',
                        embedding VECTOR(384),
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT unique_aggregate_version UNIQUE (aggregate_id, aggregate_version)
                    )
                """
                )

                # Create indexes
                await conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_embedding ON events USING ivfflat (embedding vector_cosine_ops);
                    CREATE INDEX IF NOT EXISTS idx_aggregate_id ON events (aggregate_id);
                    CREATE INDEX IF NOT EXISTS idx_aggregate_version ON events (aggregate_id, aggregate_version);
                """
                )

            finally:
                await conn.close()

        asyncio.run(init_db())

        yield dsn


@pytest.fixture
async def pgvector_store(
    postgres_container,
) -> AsyncIterator[PGVectorEventStore[MockEvent]]:
    """PGVector event store fixture."""
    store = PGVectorEventStore[MockEvent](postgres_container)
    await store.connect()
    try:
        yield store
    finally:
        if hasattr(store, "_pool") and store._pool:
            await store._pool.close()


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


async def test_pgvector_connect_error(mocker) -> None:
    """Test PGVector connection error."""
    # Mock asyncpg.create_pool to raise a connection error
    mocker.patch(
        "asyncpg.create_pool", side_effect=asyncpg.PostgresError("Connection failed")
    )

    store = PGVectorEventStore[MockEvent]("postgresql://nonexistent:5432/nonexistent")
    with pytest.raises(EventStoreConnectError) as exc_info:
        await store.connect()
    assert "Failed to connect to PostgreSQL database" in str(exc_info.value)


async def test_pgvector_transaction_error(
    pgvector_store: PGVectorEventStore[MockEvent],
) -> None:
    """Test PGVector transaction error."""
    store = pgvector_store
    with pytest.raises(ValueError) as exc_info:
        async with store._transaction():
            # Simulate transaction error
            raise ValueError("Transaction failed")
    assert "Transaction failed" in str(exc_info.value)


async def test_pgvector_append_disconnect(
    pgvector_store: PGVectorEventStore[MockEvent],
) -> None:
    """Test PGVector append with disconnect."""
    store = pgvector_store
    store._pool = None
    with pytest.raises(EventStoreTransactionError):
        await store.append(
            UUID("00000000-0000-0000-0000-000000000000"),
            [MockEvent()],
        )


async def test_pgvector_append_and_retrieve_events(
    pgvector_store: PGVectorEventStore[MockEvent],
) -> None:
    """Test appending and retrieving events."""
    aggregate_id = UUID("11111111-1111-1111-1111-111111111111")
    event1 = MockEvent()
    event2 = MockEvent()

    # Append events
    await pgvector_store.append(aggregate_id, [event1, event2])

    # Retrieve events
    events = []
    async for event in pgvector_store.get_events(aggregate_id):
        events.append(event)

    # Verify events were retrieved
    assert len(events) == 2
    assert events[0].event_id == event1.event_id
    assert events[1].event_id == event2.event_id
    assert events[0].aggregate_version == 1
    assert events[1].aggregate_version == 2


async def test_pgvector_version_conflict(
    pgvector_store: PGVectorEventStore[MockEvent],
) -> None:
    """Test version conflict detection."""
    aggregate_id = UUID("22222222-2222-2222-2222-222222222222")
    event1 = MockEvent()
    event2 = MockEvent()

    # First append should succeed
    await pgvector_store.append(aggregate_id, [event1])

    # Second append with wrong expected version should fail
    with pytest.raises(EventStoreVersionConflict):
        await pgvector_store.append(aggregate_id, [event2], expected_version=0)
