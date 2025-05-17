"""Pytest configuration and fixtures for event store tests."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, AsyncIterator, Dict, TypeVar, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from pydantic import ConfigDict, Field

from uno.domain.events import DomainEvent
from uno.persistence.event_store import PostgreSQLEventStore
from uno.event_store.redis.redis import RedisEventStore
from uno.event_store.config import EventStoreSettings
from uno.injection import ContainerProtocol
from uno.logging import LoggerProtocol


# Type variable for test events
E = TypeVar("E", bound=DomainEvent)


# Test event class
class MockEvent(DomainEvent):
    """Test event class for event store tests."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str = "test_event"
    timestamp: datetime = Field(default_factory=datetime.now)
    version: int = Field(default=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    data: dict[str, Any] = Field(default_factory=dict)

    @property
    def state(self) -> dict[str, Any]:
        """Get the event state as a dictionary."""
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            **self.data,
        }


# Fixtures
@pytest.fixture
def mock_container() -> MagicMock:
    """Create a mock container for dependency injection."""
    container = MagicMock(spec=ContainerProtocol)
    return container


@pytest.fixture
def mock_settings() -> EventStoreSettings:
    """Create test settings for the event store."""
    return EventStoreSettings(
        postgres_dsn="postgresql://test:test@localhost:5432/testdb",
        postgres_pool_min_size=1,
        postgres_pool_max_size=5,
        postgres_enable_vector_search=True,
        postgres_vector_dimensions=384,
    )


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger."""
    logger = MagicMock(spec=LoggerProtocol)
    return logger


# PostgreSQL-specific fixtures
@pytest_asyncio.fixture
async def postgres_event_store(
    mock_container: MagicMock,
    mock_settings: EventStoreSettings,
    mock_logger: MagicMock,
) -> AsyncIterator[PostgreSQLEventStore[MockEvent]]:
    """Create and connect a PostgreSQL event store for testing."""
    store = PostgreSQLEventStore[MockEvent](
        container=mock_container, settings=mock_settings, logger=mock_logger
    )

    # Mock the connection pool
    mock_pool = AsyncMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
    store._pool = mock_pool  # type: ignore

    # Set up mock connection
    mock_conn.fetchval.return_value = 0  # For version checks
    mock_conn.fetch.return_value = []  # For empty result sets

    try:
        yield store
    finally:
        await store.disconnect()


# Redis-specific fixtures
@pytest_asyncio.fixture
async def redis_event_store(
    mock_container: MagicMock,
    mock_settings: EventStoreSettings,
    mock_logger: MagicMock,
) -> AsyncIterator[RedisEventStore[MockEvent]]:
    """Create and connect a Redis event store for testing."""
    store = RedisEventStore[MockEvent](
        container=mock_container, settings=mock_settings, logger=mock_logger
    )

    # Mock Redis client
    mock_redis = AsyncMock()
    store._redis = mock_redis  # type: ignore

    # Set up mock responses
    mock_redis.xadd.return_value = b"1-0"  # Mock stream ID
    mock_redis.xread.return_value = []  # Empty stream by default

    try:
        yield store
    finally:
        await store.disconnect()


# Common test event fixtures
@pytest.fixture
def test_event() -> MockEvent:
    """Create a test event with default values."""
    return MockEvent(
        event_id=uuid4(),
        event_type="test_event",
        timestamp=datetime.now(),
        version=1,
        data={"message": "Test event"},
    )


@pytest.fixture
def test_events() -> list[MockEvent]:
    """Create a list of test events."""
    return [
        MockEvent(
            event_id=uuid4(),
            event_type=f"test_event_{i}",
            timestamp=datetime.now(),
            version=i + 1,
            data={"message": f"Test event {i}", "index": i},
        )
        for i in range(5)
    ]
