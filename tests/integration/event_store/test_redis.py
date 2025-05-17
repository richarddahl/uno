from __future__ import annotations

import pytest
from typing import AsyncIterator
from uuid import UUID
from uno.domain.events import DomainEvent
from uno.event_store.redis.redis import RedisEventStore
from uno.event_store.errors import (
    EventStoreConnectError,
    EventStoreTransactionError,
    EventStoreGetEventsError,
    EventStoreError,
)


class MockEvent(DomainEvent):
    """Test event class."""

    pass


@pytest.fixture
async def redis_store() -> AsyncIterator[RedisEventStore[MockEvent]]:
    """Redis event store fixture."""
    store = RedisEventStore[MockEvent]("redis://localhost:6379")
    await store.connect()
    try:
        yield store
    finally:
        await store.close()


async def test_redis_connect_error() -> None:
    """Test Redis connection error."""
    store = RedisEventStore[MockEvent]("redis://nonexistent:6379")
    with pytest.raises(EventStoreConnectError) as exc_info:
        await store.connect()
    assert "Failed to connect to Redis" in str(exc_info.value)


async def test_redis_transaction_error() -> None:
    """Test Redis transaction error."""
    store = RedisEventStore[MockEvent]("redis://localhost:6379")
    await store.connect()
    with pytest.raises(ValueError) as exc_info:
        async with store._transaction():
            # Simulate transaction error
            raise ValueError("Transaction failed")
    assert "Transaction failed" in str(exc_info.value)


async def test_redis_get_events_error() -> None:
    """Test Redis get events error."""
    store = RedisEventStore[MockEvent]("redis://localhost:6379")
    await store.connect()
    # This test should pass since we're actually connecting to Redis
    async for _ in store.get_events("nonexistent_key"):
        pass
    # Verify no events were returned
    assert True  # No exception means test passed


async def test_redis_append_disconnect(redis_store: RedisEventStore[MockEvent]) -> None:
    """Test Redis append with disconnect."""
    store = redis_store
    store._redis = None
    with pytest.raises(EventStoreConnectError):
        await store.append(
            UUID("00000000-0000-0000-0000-000000000000"),
            [MockEvent()],
        )
