"""Tests for Redis Unit of Work implementation."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional, Type
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel
from redis.exceptions import RedisError

from uno.domain.aggregate import AggregateRoot
from uno.domain.events import DomainEvent
from uno.uow.errors import ConcurrencyError
from uno.uow import RedisUnitOfWork, get_current_uow


# Test aggregate and event classes
class MockEvent(DomainEvent):
    """Test event for unit testing."""

    value: str


class MockAggregate(AggregateRoot[MockEvent]):
    """Test aggregate for unit testing."""

    def __init__(self, id: UUID, value: str = ""):
        super().__init__(id)
        self.value = value

    def apply_event(self, event: MockEvent) -> None:
        """Apply a test event to the aggregate."""
        self.value = event.value

    @classmethod
    def create(cls, id: UUID, value: str) -> MockAggregate:
        """Create a new test aggregate."""
        aggregate = cls(id)
        event = MockEvent(
            aggregate_id=str(id),
            version=1,
            value=value,
        )
        aggregate._apply_event(event)
        return aggregate

    def update(self, value: str) -> None:
        """Update the aggregate value."""
        event = MockEvent(
            aggregate_id=str(self.id),
            version=self.version + 1,
            value=value,
        )
        self._apply_event(event)


# Fixtures
@pytest.fixture
def mock_redis() -> MagicMock:
    """Create a mock Redis client."""
    return MagicMock()


@pytest.fixture
def mock_container() -> MagicMock:
    """Create a mock container."""
    return MagicMock()


@pytest.fixture
async def uow(
    mock_redis: MagicMock, mock_container: MagicMock
) -> RedisUnitOfWork[MockAggregate, MockEvent]:
    """Create a RedisUnitOfWork instance for testing."""
    return RedisUnitOfWork[MockAggregate, MockEvent](
        container=mock_container,
        redis=mock_redis,
    )


# Tests
class TestRedisUnitOfWork:
    """Tests for RedisUnitOfWork class."""

    async def test_begin_creates_transaction(
        self, uow: RedisUnitOfWork[MockAggregate, MockEvent], mock_redis: MagicMock
    ) -> None:
        """Test that begin() creates a new transaction."""
        assert uow.transaction is mock_redis

        await uow.begin()
        assert uow.transaction is not mock_redis
        assert uow.in_transaction

    async def test_commit_executes_transaction(
        self, uow: RedisUnitOfWork[MockAggregate, MockEvent], mock_redis: MagicMock
    ) -> None:
        """Test that commit() executes the transaction."""
        await uow.begin()
        await uow.commit()

        uow.transaction.execute.assert_awaited_once()
        assert not uow.in_transaction

    async def test_rollback_resets_transaction(
        self, uow: RedisUnitOfWork[MockAggregate, MockEvent], mock_redis: MagicMock
    ) -> None:
        """Test that rollback() resets the transaction."""
        await uow.begin()
        await uow.rollback()

        uow.transaction.reset.assert_awaited_once()
        assert not uow.in_transaction

    async def test_nested_transactions_use_savepoints(
        self, uow: RedisUnitOfWork[MockAggregate, MockEvent], mock_redis: MagicMock
    ) -> None:
        """Test that nested transactions use savepoints."""
        await uow.begin()
        assert uow.transaction_depth == 1

        # Nested transaction
        await uow.begin()
        assert uow.transaction_depth == 2

        # Commit nested transaction
        await uow.commit()
        assert uow.transaction_depth == 1

        # Another nested transaction
        await uow.begin()
        assert uow.transaction_depth == 2

        # Rollback nested transaction
        await uow.rollback()
        assert uow.transaction_depth == 1

    async def test_track_aggregate_adds_to_tracking(
        self, uow: RedisUnitOfWork[MockAggregate, MockEvent]
    ) -> None:
        """Test that track_aggregate() adds the aggregate to tracking."""
        aggregate = MockAggregate.create(uuid4(), "test")

        await uow.begin()
        uow.track_aggregate(aggregate)

        assert aggregate.id in uow._tracked_aggregates
        assert uow._aggregate_versions[aggregate.id] == aggregate.version

    async def test_get_current_uow_returns_current_uow(
        self, uow: RedisUnitOfWork[MockAggregate, MockEvent]
    ) -> None:
        """Test that get_current_uow() returns the current UoW."""
        async with uow:
            current = get_current_uow()
            assert current is uow


class TestRedisRepository:
    """Tests for RedisRepository class."""

    async def test_get_returns_aggregate(
        self, mock_redis: MagicMock, uow: RedisUnitOfWork[MockAggregate, MockEvent]
    ) -> None:
        """Test that get() returns an aggregate from Redis."""
        # TODO: Implement once Redis serialization is in place
        pass

    async def test_add_stores_aggregate(
        self, mock_redis: MagicMock, uow: RedisUnitOfWork[MockAggregate, MockEvent]
    ) -> None:
        """Test that add() stores an aggregate in Redis."""
        # TODO: Implement once Redis serialization is in place
        pass

    async def test_delete_removes_aggregate(
        self, mock_redis: MagicMock, uow: RedisUnitOfWork[MockAggregate, MockEvent]
    ) -> None:
        """Test that delete() removes an aggregate from Redis."""
        aggregate_id = uuid4()
        repo = uow.get_repository(MockAggregate)

        await repo.delete(aggregate_id)

        key = f"aggregate:testaggregate:{aggregate_id}"
        mock_redis.delete.assert_awaited_once_with(key)
