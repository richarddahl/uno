"""Tests for the DeadLetterQueue implementation."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from uno.event_bus.dead_letter import (
    DeadLetterEvent,
    DeadLetterQueue,
    DeadLetterReason,
)
from uno.metrics import Metrics


class TestEvent(BaseModel):
    """Test event model for dead letter queue tests."""
    id: str
    name: str
    timestamp: datetime = datetime.now(timezone.utc)


@pytest.fixture
def mock_metrics() -> Metrics:
    """Fixture providing a mock metrics instance."""
    with patch('uno.metrics.Metrics') as mock_metrics_cls:
        mock_metrics = MagicMock(spec=Metrics)
        mock_metrics_cls.return_value = mock_metrics
        yield mock_metrics


@pytest.fixture
def dead_letter_queue(mock_metrics: Metrics) -> DeadLetterQueue[TestEvent]:
    """Fixture providing a DeadLetterQueue instance for testing."""
    return DeadLetterQueue[TestEvent](metrics=mock_metrics)


class TestDeadLetterEvent:
    """Tests for DeadLetterEvent class."""

    def test_from_event_with_model(self) -> None:
        """Test creating a DeadLetterEvent from a Pydantic model."""
        event = TestEvent(id="123", name="test")
        dl_event = DeadLetterEvent.from_event(
            event=event,
            reason=DeadLetterReason.HANDLER_FAILED,
            error=ValueError("Test error"),
            subscription_id="test-sub",
            attempt_count=2,
            custom_meta={"key": "value"}
        )
        
        assert dl_event.event_data == event.model_dump()
        assert dl_event.reason == DeadLetterReason.HANDLER_FAILED
        assert dl_event.error == "ValueError: Test error"
        assert dl_event.subscription_id == "test-sub"
        assert dl_event.attempt_count == 2
        assert dl_event.metadata["custom_meta"] == {"key": "value"}

    def test_from_event_with_dict(self) -> None:
        """Test creating a DeadLetterEvent from a dictionary."""
        event_data = {"id": "123", "name": "test"}
        dl_event = DeadLetterEvent.from_event(
            event=event_data,
            reason=DeadLetterReason.HANDLER_FAILED,
        )
        
        assert dl_event.event_data == event_data
        assert dl_event.reason == DeadLetterReason.HANDLER_FAILED


class TestDeadLetterQueue:
    """Tests for DeadLetterQueue class."""

    async def test_add_event(
        self,
        dead_letter_queue: DeadLetterQueue[TestEvent],
        mock_metrics: MagicMock
    ) -> None:
        """Test adding an event to the dead letter queue."""
        event = TestEvent(id="123", name="test")
        
        await dead_letter_queue.add(
            event=event,
            reason=DeadLetterReason.HANDLER_FAILED,
            error=ValueError("Test error"),
            subscription_id="test-sub",
            attempt_count=2,
        )
        
        # Verify metrics were recorded
        mock_metrics.increment.assert_called_once_with(
            "event.dead_lettered",
            tags={
                "reason": "handler_failed",
                "event_type": "TestEvent",
                "subscription_id": "test-sub"
            }
        )
        
        # Verify error was recorded
        assert mock_metrics.record_exception.called
        
        # Verify event was stored
        assert len(dead_letter_queue._queue) == 1
        dl_event = dead_letter_queue._queue[0]
        assert dl_event.event_data == event.model_dump()
        assert dl_event.reason == DeadLetterReason.HANDLER_FAILED

    async def test_process_events(
        self,
        dead_letter_queue: DeadLetterQueue[TestEvent],
        mock_metrics: MagicMock
    ) -> None:
        """Test processing events with a handler."""
        # Add test event
        event = TestEvent(id="123", name="test")
        await dead_letter_queue.add(
            event=event,
            reason=DeadLetterReason.HANDLER_FAILED,
        )
        
        # Setup mock handler
        mock_handler = AsyncMock()
        handler_id = dead_letter_queue.add_handler(mock_handler)
        
        # Process events
        await dead_letter_queue.process()
        
        # Verify handler was called with the dead letter event
        mock_handler.assert_awaited_once()
        dl_event = mock_handler.await_args[0][0]
        assert isinstance(dl_event, DeadLetterEvent)
        assert dl_event.event_data == event.model_dump()
        
        # Verify metrics were recorded
        mock_metrics.increment.assert_any_call(
            "event.dead_lettered",
            tags={
                "reason": "handler_failed",
                "event_type": "TestEvent",
                "subscription_id": ""
            }
        )
        mock_metrics.increment.assert_any_call(
            "event.dead_letter.processed",
            tags={"status": "success"}
        )

    async def test_process_events_with_retry(
        self,
        dead_letter_queue: DeadLetterQueue[TestEvent]
    ) -> None:
        """Test processing events with retry logic."""
        # Setup mock handler that fails first time, then succeeds
        mock_handler = AsyncMock()
        mock_handler.side_effect = [
            Exception("First failure"),
            None  # Success on retry
        ]
        
        dead_letter_queue.add_handler(mock_handler)
        
        # Add test event
        event = TestEvent(id="123", name="test")
        await dead_letter_queue.add(
            event=event,
            reason=DeadLetterReason.HANDLER_FAILED,
        )
        
        # Process with retry
        with patch("asyncio.sleep") as mock_sleep:
            await dead_letter_queue.process(max_attempts=2, retry_delay=0.1)
            
            # Verify sleep was called for the retry
            mock_sleep.assert_called_once_with(0.1)
            
            # Verify handler was called twice (initial + retry)
            assert mock_handler.await_count == 2

    async def test_remove_handler(
        self,
        dead_letter_queue: DeadLetterQueue[TestEvent]
    ) -> None:
        """Test removing an event handler."""
        # Add two handlers
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        
        handler1_id = dead_letter_queue.add_handler(handler1)
        dead_letter_queue.add_handler(handler2)
        
        # Remove first handler
        dead_letter_queue.remove_handler(handler1_id)
        
        # Process events - only handler2 should be called
        await dead_letter_queue.add(
            event=TestEvent(id="123", name="test"),
            reason=DeadLetterReason.HANDLER_FAILED,
        )
        await dead_letter_queue.process()
        
        handler1.assert_not_awaited()
        handler2.assert_awaited_once()

    async def test_clear_handlers(
        self,
        dead_letter_queue: DeadLetterQueue[TestEvent]
    ) -> None:
        """Test clearing all event handlers."""
        # Add handlers
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        
        dead_letter_queue.add_handler(handler1)
        dead_letter_queue.add_handler(handler2)
        
        # Clear handlers
        dead_letter_queue.clear_handlers()
        
        # Process events - no handlers should be called
        await dead_letter_queue.add(
            event=TestEvent(id="123", name="test"),
            reason=DeadLetterReason.HANDLER_FAILED,
        )
        await dead_letter_queue.process()
        
        handler1.assert_not_awaited()
        handler2.assert_not_awaited()

    async def test_metrics_on_handler_error(
        self,
        dead_letter_queue: DeadLetterQueue[TestEvent],
        mock_metrics: MagicMock
    ) -> None:
        """Test metrics are recorded when a handler raises an exception."""
        # Setup failing handler
        mock_handler = AsyncMock(side_effect=Exception("Handler failed"))
        dead_letter_queue.add_handler(mock_handler)
        
        # Add test event
        await dead_letter_queue.add(
            event=TestEvent(id="123", name="test"),
            reason=DeadLetterReason.HANDLER_FAILED,
        )
        
        # Process events - should not raise
        await dead_letter_queue.process()
        
        # Verify error metrics were recorded
        mock_metrics.increment.assert_any_call(
            "event.dead_letter.processed",
            tags={"status": "error"}
        )
        assert mock_metrics.record_exception.called

    async def test_retry_policy_configuration(
        self,
        dead_letter_queue: DeadLetterQueue[TestEvent]
    ) -> None:
        """Test configuring custom retry policy."""
        # Custom retry policy with exponential backoff
        def retry_policy(attempt: int) -> float | None:
            if attempt > 2:  # Max 2 retries
                return None
            return 0.1 * (2 ** attempt)  # Exponential backoff
        
        dead_letter_queue.set_retry_policy(retry_policy, max_attempts=3)
        
        # Setup mock handler that always fails
        mock_handler = AsyncMock(side_effect=Exception("Failed"))
        dead_letter_queue.add_handler(mock_handler)
        
        # Add test event
        await dead_letter_queue.add(
            event=TestEvent(id="123", name="test"),
            reason=DeadLetterReason.HANDLER_FAILED,
        )
        
        # Process with retry policy
        with patch("asyncio.sleep") as mock_sleep:
            await dead_letter_queue.process()
            
            # Verify sleep was called with exponential backoff delays
            assert mock_sleep.call_count == 2  # 2 retries
            assert 0.19 <= mock_sleep.call_args_list[0][0][0] <= 0.21  # ~0.2s
            assert 0.39 <= mock_sleep.call_args_list[1][0][0] <= 0.41  # ~0.4s

    async def test_metrics_on_retry(
        self,
        dead_letter_queue: DeadLetterQueue[TestEvent],
        mock_metrics: MagicMock
    ) -> None:
        """Test metrics are recorded for retry attempts."""
        # Setup mock handler that fails first time, then succeeds
        mock_handler = AsyncMock(side_effect=[
            Exception("First failure"),
            None  # Success on retry
        ])
        dead_letter_queue.add_handler(mock_handler)
        
        # Add test event
        await dead_letter_queue.add(
            event=TestEvent(id="123", name="test"),
            reason=DeadLetterReason.HANDLER_FAILED,
        )
        
        # Process with retry
        with patch("asyncio.sleep"):
            await dead_letter_queue.process(max_attempts=2, retry_delay=0.1)
            
            # Verify retry metrics were recorded
            mock_metrics.increment.assert_any_call(
                "event.dead_letter.retry",
                tags={"attempt": "1", "delay": "0.10"}
            )
            mock_metrics.increment.assert_any_call(
                "event.dead_letter.processed",
                tags={"status": "success"}
            )

    async def test_event_serialization(self) -> None:
        """Test that events can be properly serialized and deserialized."""
        # Create a dead letter event with a complex event
        event = TestEvent(
            id="123",
            name="test",
            timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc)
        )
        dl_event = DeadLetterEvent.from_event(
            event=event,
            reason=DeadLetterReason.HANDLER_FAILED,
            error=ValueError("Test error"),
            subscription_id="test-sub",
            attempt_count=1,
        )
        
        # Convert to dict and back
        data = dl_event.model_dump()
        rehydrated = DeadLetterEvent.model_validate(data)
        
        # Should match original
        assert rehydrated.event_data == event.model_dump()
        assert rehydrated.reason == DeadLetterReason.HANDLER_FAILED
        assert rehydrated.error == "ValueError: Test error"
        assert rehydrated.subscription_id == "test-sub"
        assert rehydrated.attempt_count == 1
        assert rehydrated.timestamp == dl_event.timestamp
