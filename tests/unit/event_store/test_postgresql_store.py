"""Unit tests for PostgreSQL event store implementation."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from uno.domain.events import DomainEvent
from uno.persistence.event_store import PostgreSQLEventStore
from uno.event_store.errors import (
    EventStoreError,
    EventStoreAppendError,
    EventStoreVersionConflict,
    EventStoreGetEventsError,
)


class TestPostgreSQLEventStoreBasic:
    """Basic tests for PostgreSQL event store."""

    async def test_initialization(
        self,
        postgres_event_store: PostgreSQLEventStore[DomainEvent],
    ) -> None:
        """Test that the store initializes correctly."""
        assert postgres_event_store is not None
        assert postgres_event_store.settings is not None
        assert postgres_event_store.logger is not None

    async def test_connect_disconnect(
        self,
        postgres_event_store: PostgreSQLEventStore[DomainEvent],
    ) -> None:
        """Test connecting and disconnecting from the store."""
        # Connection is established by the fixture
        assert postgres_event_store._pool is not None

        # Test disconnect
        await postgres_event_store.disconnect()
        assert postgres_event_store._pool is None

    async def test_connection_pool_management(
        self,
        postgres_event_store: PostgreSQLEventStore[DomainEvent],
    ) -> None:
        """Test connection pool management."""
        # Get a connection from the pool
        async with postgres_event_store._get_connection() as conn:
            assert conn is not None
            # Verify the connection was acquired from the pool
            postgres_event_store._pool.acquire.assert_called_once()  # type: ignore


class TestPostgreSQLEventStoreOperations:
    """Tests for PostgreSQL event store operations."""

    async def test_append_event(
        self,
        postgres_event_store: PostgreSQLEventStore[DomainEvent],
        test_event: DomainEvent,
    ) -> None:
        """Test appending a single event."""
        aggregate_id = uuid4()

        # Mock the execute method to return a row count
        mock_conn = postgres_event_store._pool.acquire.return_value.__aenter__.return_value  # type: ignore
        mock_conn.fetchval.return_value = 1  # Simulate one row inserted

        # Test append
        await postgres_event_store.append(
            aggregate_id=str(aggregate_id),
            events=[test_event],
        )

        # Verify the event was inserted
        mock_conn.execute.assert_called_once()

    async def test_append_multiple_events(
        self,
        postgres_event_store: PostgreSQLEventStore[DomainEvent],
        test_events: list[DomainEvent],
    ) -> None:
        """Test appending multiple events in a transaction."""
        aggregate_id = uuid4()

        # Mock the execute method to return a row count
        mock_conn = postgres_event_store._pool.acquire.return_value.__aenter__.return_value  # type: ignore
        mock_conn.fetchval.return_value = len(test_events)  # Simulate rows inserted

        # Test append
        await postgres_event_store.append(
            aggregate_id=str(aggregate_id),
            events=test_events,
        )

        # Verify the events were inserted in a transaction
        assert mock_conn.execute.call_count == len(test_events)
        mock_conn.execute.assert_called()

    async def test_append_with_version_conflict(
        self,
        postgres_event_store: PostgreSQLEventStore[DomainEvent],
        test_event: DomainEvent,
    ) -> None:
        """Test that a version conflict raises the correct error."""
        aggregate_id = uuid4()

        # Mock the execute method to return 0 rows (simulating version conflict)
        mock_conn = postgres_event_store._pool.acquire.return_value.__aenter__.return_value  # type: ignore
        mock_conn.fetchval.return_value = 0

        # Test append with expected version
        with pytest.raises(EventStoreVersionConflict):
            await postgres_event_store.append(
                aggregate_id=str(aggregate_id),
                events=[test_event],
                expected_version=1,  # This should cause a conflict
            )

    async def test_get_events(
        self,
        postgres_event_store: PostgreSQLEventStore[DomainEvent],
        test_events: list[DomainEvent],
    ) -> None:
        """Test retrieving events for an aggregate."""
        aggregate_id = uuid4()

        # Mock the fetch method to return test events
        mock_conn = postgres_event_store._pool.acquire.return_value.__aenter__.return_value  # type: ignore
        mock_conn.fetch.return_value = [
            (
                str(agg_id),
                str(event.event_id),
                event.event_type,
                event.version,
                event.timestamp.isoformat(),
                event.model_dump_json(),
                event.metadata,
            )
            for agg_id, event in zip([aggregate_id] * len(test_events), test_events)
        ]

        # Test get_events
        events = await postgres_event_store.get_events(aggregate_id=str(aggregate_id))

        # Verify the events were retrieved
        assert len(events) == len(test_events)
        assert all(isinstance(event, DomainEvent) for event in events)


class TestPostgreSQLEventStoreEdgeCases:
    """Tests for edge cases and error conditions."""

    async def test_append_empty_events(
        self,
        postgres_event_store: PostgreSQLEventStore[DomainEvent],
    ) -> None:
        """Test that appending an empty list of events is a no-op."""
        # This should not raise an exception
        await postgres_event_store.append(
            aggregate_id=str(uuid4()),
            events=[],
        )

        # Verify no database operations were performed
        postgres_event_store._pool.acquire.assert_not_called()  # type: ignore

    async def test_get_events_nonexistent_aggregate(
        self,
        postgres_event_store: PostgreSQLEventStore[DomainEvent],
    ) -> None:
        """Test retrieving events for a non-existent aggregate returns empty list."""
        # Mock the fetch method to return no results
        mock_conn = postgres_event_store._pool.acquire.return_value.__aenter__.return_value  # type: ignore
        mock_conn.fetch.return_value = []

        # Test get_events for non-existent aggregate
        events = await postgres_event_store.get_events(aggregate_id=str(uuid4()))

        # Verify an empty list is returned
        assert events == []

    async def test_connection_error_handling(
        self,
        postgres_event_store: PostgreSQLEventStore[DomainEvent],
        test_event: DomainEvent,
    ) -> None:
        """Test that connection errors are properly handled."""
        # Simulate a connection error
        mock_conn = postgres_event_store._pool.acquire.return_value.__aenter__
        mock_conn.side_effect = ConnectionError("Connection failed")

        # Test that the error is properly wrapped
        with pytest.raises(EventStoreError) as exc_info:
            await postgres_event_store.append(
                aggregate_id=str(uuid4()),
                events=[test_event],
            )

        assert "Connection failed" in str(exc_info.value)
