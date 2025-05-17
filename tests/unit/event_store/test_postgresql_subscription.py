"""Tests for PostgreSQL event store subscription functionality."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest
from pydantic import BaseModel, Field

from uno.domain.events import DomainEvent
from uno.persistence.event_store import Subscription, SubscriptionManager


# Helper function to replace uno.testing.async_test
# This is a simplified version for testing purposes
def async_test(f):
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


class MockEvent(DomainEvent):
    """Test event for subscription tests."""

    event_type: str = "test_event"
    aggregate_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    aggregate_version: int = 1
    value: str = "test"


@pytest.fixture
def mock_pool() -> AsyncMock:
    """Create a mock asyncpg pool."""
    pool = AsyncMock(spec=asyncpg.Pool)
    connection = AsyncMock(spec=asyncpg.Connection)
    pool.acquire.return_value.__aenter__.return_value = connection
    return pool


@pytest.fixture
def subscription_manager(mock_pool: AsyncMock) -> SubscriptionManager:
    """Create a subscription manager with a mock pool."""
    return SubscriptionManager(mock_pool)


@async_test
async def test_subscribe(subscription_manager: SubscriptionManager) -> None:
    """Test subscribing to a channel."""
    mock_handler = AsyncMock()

    await subscription_manager.subscribe("test_channel", mock_handler)

    # Verify the handler was added
    assert "test_channel" in subscription_manager._subscriptions
    assert mock_handler in subscription_manager._subscriptions["test_channel"].handlers

    # Verify LISTEN was called
    connection = await subscription_manager._pool.acquire()
    await connection.execute.assert_called_once_with('LISTEN "test_channel"')


@async_test
async def test_unsubscribe(subscription_manager: SubscriptionManager) -> None:
    """Test unsubscribing from a channel."""
    mock_handler = AsyncMock()

    # First subscribe
    await subscription_manager.subscribe("test_channel", mock_handler)

    # Then unsubscribe
    await subscription_manager.unsubscribe("test_channel", mock_handler)

    # Verify the handler was removed
    assert "test_channel" not in subscription_manager._subscriptions


@async_test
async def test_notification_handling(subscription_manager: SubscriptionManager) -> None:
    """Test handling of incoming notifications."""
    mock_handler = AsyncMock()
    test_event = MockEvent(value="test")

    # Subscribe to the channel
    await subscription_manager.subscribe("test_channel", mock_handler)

    # Get the subscription
    subscription = subscription_manager._subscriptions["test_channel"]

    # Simulate a notification
    subscription._notification_handler(
        connection=MagicMock(),
        pid=123,
        channel="test_channel",
        payload=test_event.model_dump_json(),
    )

    # Verify the handler was called with the correct event
    mock_handler.assert_called_once()
    event_arg = mock_handler.call_args[0][0]
    assert isinstance(event_arg, MockEvent)
    assert event_arg.value == "test"


@async_test
async def test_close(subscription_manager: SubscriptionManager) -> None:
    """Test closing the subscription manager."""
    # Add a subscription
    mock_handler = AsyncMock()
    await subscription_manager.subscribe("test_channel", mock_handler)

    # Close the manager
    await subscription_manager.close()

    # Verify the subscription was cleaned up
    assert not subscription_manager._subscriptions

    # Verify the connection was released
    subscription_manager._pool.release.assert_awaited_once()


@async_test
async def test_context_manager(subscription_manager: SubscriptionManager) -> None:
    """Test using the subscription manager as a context manager."""
    async with subscription_manager as mgr:
        assert mgr is subscription_manager

    # Verify close was called on exit
    assert not subscription_manager._subscriptions
