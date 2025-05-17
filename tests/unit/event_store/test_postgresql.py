# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""Tests for PostgreSQL event store implementation."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, AsyncIterator
from uuid import UUID, uuid4

import pytest
import numpy as np
from pydantic import ConfigDict, Field

from uno.domain.events import DomainEvent
from uno.persistence.event_store import PostgreSQLEventStore
from uno.event_store.errors import (
    EventStoreAppendError,
    EventStoreGetEventsError,
    EventStoreVersionConflict,
)
from uno.logging import LoggerProtocol


# Test event class
class MockEvent(DomainEvent):
    """Test event class for PostgreSQL event store tests."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str = "test_event"
    timestamp: datetime = Field(default_factory=datetime.now)
    version: int = Field(default=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Test-specific fields
    _value: str = ""
    _number: int = 0

    @property
    def value(self) -> str:
        return self._value

    @property
    def number(self) -> int:
        return self._number

    @property
    def state(self) -> dict[str, Any]:
        """Get event state as dict."""
        return {"value": self._value, "number": self._number}

    @classmethod
    def create(cls, value: str = "", number: int = 0, **kwargs: Any) -> "MockEvent":
        """Create a test event with the given values."""
        event = cls(**kwargs)
        event._value = value
        event._number = number
        return event

    def __post_init__(self) -> None:
        # Handle state_data if provided in kwargs
        if hasattr(self, "state_data"):
            state_data = getattr(self, "state_data")
            self._value = state_data.get("value", "")
            self._number = state_data.get("number", 0)
            delattr(self, "state_data")


# Fixtures
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture
def mock_container():
    """Create a properly typed mock container for DI."""
    container = MagicMock()
    container.resolve = MagicMock(side_effect=lambda x: x)
    return container


@pytest.fixture
def mock_config() -> MagicMock:
    """Create a properly typed mock config with test values."""
    from uno.event_store.config import EventStoreSettings

    # Create a real EventStoreSettings instance with test values
    return EventStoreSettings(
        postgres_dsn="postgresql://test:test@localhost:5432/test",
        postgres_enable_vector_search=True,
        postgres_vector_dimensions=128,
        postgres_pool_min_size=1,
        postgres_pool_max_size=5,
    )


@pytest.fixture
def mock_logger():
    """Create a properly typed mock logger."""
    logger = MagicMock(spec=LoggerProtocol)
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.debug = MagicMock()
    logger.exception = MagicMock()
    return logger


@pytest.fixture
def event_store(
    mock_container: MagicMock, mock_config: MagicMock, mock_logger: MagicMock
) -> PostgreSQLEventStore[MockEvent]:
    """Create a PostgreSQL event store for testing."""
    store = PostgreSQLEventStore[MockEvent](
        container=mock_container, config=mock_config, logger=mock_logger
    )
    return store  # type: ignore[return-value]


@pytest.fixture
def test_event() -> MockEvent:
    """Create a test event."""
    return MockEvent.create(
        event_type="test_event",
        value="test",
        number=42,
        metadata={"source": "test"},
    )


@pytest.fixture
async def mock_pool():
    """Create a mock connection pool."""
    pool = AsyncMock()
    conn = AsyncMock()
    pool.acquire.return_value.__aenter__.return_value = conn
    pool.acquire.return_value.__aexit__.return_value = None
    return pool


@pytest.fixture
async def connected_event_store(
    event_store: PostgreSQLEventStore[MockEvent], mock_pool: AsyncMock
) -> AsyncIterator[PostgreSQLEventStore[MockEvent]]:
    """Create and connect a PostgreSQL event store."""
    # Mock the pool creation
    event_store._pool = mock_pool  # type: ignore[assignment]

    # Mock the necessary methods
    event_store._setup_vector_extension = AsyncMock()  # type: ignore[method-assign]
    event_store._create_tables = AsyncMock()  # type: ignore[method-assign]
    event_store._create_indexes = AsyncMock()  # type: ignore[method-assign]

    # Set up vector extension as available
    event_store._vector_extension_available = True  # type: ignore[assignment]

    # Connect to the mock database
    await event_store.connect()

    try:
        yield event_store
    finally:
        if event_store._pool:
            event_store._pool = None


# Tests
class TestPostgreSQLEventStore:
    """Tests for PostgreSQL event store."""

    async def test_connect(self, event_store: PostgreSQLEventStore[MockEvent]) -> None:
        """Test connecting to the database."""
        await event_store.connect()
        assert event_store._pool is not None

    async def test_append_and_get_events(
        self,
        connected_event_store: PostgreSQLEventStore[MockEvent],
        test_event: MockEvent,
    ) -> None:
        """Test appending and retrieving events."""
        aggregate_id = uuid4()

        # Append events
        await connected_event_store.append(aggregate_id, [test_event])

        # Get events
        events = []
        async for event in connected_event_store.get_events(aggregate_id):
            events.append(event)

        assert len(events) == 1
        assert events[0].event_type == "test_event"
        assert events[0].state["value"] == "test"
        assert events[0].state["number"] == 42
        assert events[0].metadata.get("source") == "test"

    async def test_append_with_expected_version(
        self,
        connected_event_store: PostgreSQLEventStore[MockEvent],
        test_event: MockEvent,
    ) -> None:
        """Test appending with expected version."""
        aggregate_id = uuid4()

        # First append
        await connected_event_store.append(aggregate_id, [test_event])

        # Second append with correct expected version
        await connected_event_store.append(
            aggregate_id, [test_event], expected_version=1
        )

        # Should have 2 events now
        events = []
        async for event in connected_event_store.get_events(aggregate_id):
            events.append(event)

        assert len(events) == 2

    async def test_append_with_wrong_expected_version(
        self,
        connected_event_store: PostgreSQLEventStore[MockEvent],
        test_event: MockEvent,
    ) -> None:
        """Test appending with wrong expected version raises error."""
        aggregate_id = uuid4()

        # First append
        await connected_event_store.append(aggregate_id, [test_event])

        # Second append with wrong expected version
        with pytest.raises(EventStoreVersionConflict):
            await connected_event_store.append(
                aggregate_id, [test_event], expected_version=42
            )

    async def test_replay_events(
        self,
        connected_event_store: PostgreSQLEventStore[MockEvent],
        test_event: MockEvent,
    ) -> None:
        """Test replaying events."""
        aggregate_id = uuid4()

        # Append multiple events
        for i in range(5):
            event = MockEvent(
                event_type=f"test_event_{i}",
                state_data={"value": f"test_{i}", "number": i},
            )
            await connected_event_store.append(aggregate_id, [event])

        # Replay events with version range
        events = []
        async for event in connected_event_store.replay_events(
            aggregate_id, from_version=2, to_version=4, batch_size=2
        ):
            events.append(event)

        assert len(events) == 3  # Versions 2, 3, 4
        assert events[0].event_type == "test_event_1"  # Version 2 (0-based index)
        assert events[1].event_type == "test_event_2"
        assert events[2].event_type == "test_event_3"

    async def test_vector_search(
        self,
        connected_event_store: PostgreSQLEventStore[MockEvent],
        test_event: MockEvent,
    ) -> None:
        """Test vector similarity search."""
        if not connected_event_store._vector_extension_available:
            pytest.skip("pgvector extension not available")

        aggregate_id = uuid4()

        # Create test embeddings
        embeddings = [
            [0.1] * 1536,  # Similar to query
            [0.9] * 1536,  # Less similar
            [0.2] * 1536,  # Similar to query
            [0.8] * 1536,  # Less similar
        ]

        # Append events with embeddings
        for i in range(4):
            event = MockEvent(
                event_type=f"test_event_{i}",
                state_data={"value": f"test_{i}", "number": i},
            )
            await connected_event_store.append(
                aggregate_id, [event], embeddings=[embeddings[i]]
            )

        # Search with a query embedding similar to the first and third events
        query_embedding = [0.15] * 1536
        results = await connected_event_store.search_events_by_vector(
            query_embedding=query_embedding,
            limit=2,
            similarity_threshold=0.5,
        )

        # Should return the most similar events first
        assert len(results) == 2
        assert (
            "test_0" in results[0].state["value"]
            or "test_2" in results[0].state["value"]
        )
        assert (
            "test_0" in results[1].state["value"]
            or "test_2" in results[1].state["value"]
        )

    async def test_metrics(
        self,
        connected_event_store: PostgreSQLEventStore[MockEvent],
        test_event: MockEvent,
    ) -> None:
        """Test getting database metrics."""
        aggregate_id = uuid4()

        # Add some events
        for i in range(3):
            event = MockEvent(
                event_type=f"test_event_{i}",
                state_data={"value": f"test_{i}", "number": i},
            )
            await connected_event_store.append(aggregate_id, [event])

        # Get metrics
        metrics = await connected_event_store.get_metrics()

        # Check basic metrics
        assert metrics["event_count"] == 3
        assert metrics["aggregate_count"] == 1
        assert (
            metrics["vector_search_enabled"]
            == connected_event_store._vector_extension_available
        )

    async def test_vacuum(
        self, connected_event_store: PostgreSQLEventStore[MockEvent]
    ) -> None:
        """Test running VACUUM and ANALYZE."""
        # This just tests that the method runs without errors
        await connected_event_store.vacuum(full=False, analyze=True)
