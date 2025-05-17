# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""Tests for key rotation scheduler."""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Coroutine, cast

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from uno.config.key_scheduler import KeyRotationScheduler, get_rotation_scheduler
from uno.config.key_policy import (
    TimeBasedRotationPolicy,
    UsageBasedRotationPolicy,
    RotationReason,
)


@pytest.fixture
def mock_secure_value_class() -> MagicMock:
    """Create a mocked SecureValue class."""
    mock = MagicMock()
    mock._current_key_version = "v1"
    mock._encryption_keys = {"v1": b"test-key"}
    return mock


@pytest.fixture
def mock_key_history() -> AsyncMock:
    """Create a mocked KeyHistory."""
    mock = AsyncMock()
    mock.record_policy_check = AsyncMock()
    mock.record_key_rotated = AsyncMock()
    mock.get_version_info.return_value = {
        "creation_time": time.time() - 86400,
        "last_rotation_time": 0,
        "last_usage_time": time.time() - 3600,
        "usage_count": 100,
        "active": True,
    }
    return mock


class TestKeyRotationScheduler:
    """Tests for KeyRotationScheduler."""

    def test_singleton_pattern(self) -> None:
        """Test that KeyRotationScheduler uses the singleton pattern."""
        # Get two instances
        scheduler1 = KeyRotationScheduler.get_instance()
        scheduler2 = KeyRotationScheduler.get_instance()

        # Should be the same object
        assert scheduler1 is scheduler2

        # get_rotation_scheduler should return the same instance
        scheduler3 = get_rotation_scheduler()
        assert scheduler1 is scheduler3

    def test_configure(self) -> None:
        """Test scheduler configuration."""
        # Create a clean instance
        scheduler = KeyRotationScheduler()

        # Default check interval
        assert scheduler._check_interval == 3600

        # Configure with custom values
        time_policy = TimeBasedRotationPolicy(max_age_days=5)
        usage_policy = UsageBasedRotationPolicy(max_uses=500)

        # Custom key provider
        async def test_key_provider() -> tuple[str, bytes]:
            return "test-version", b"test-key"

        scheduler.configure(
            check_interval=300,
            policies=[time_policy, usage_policy],
            key_provider=test_key_provider,
        )

        # Verify configuration
        assert scheduler._check_interval == 300
        assert len(scheduler._policies) == 2
        assert isinstance(scheduler._policies[0], TimeBasedRotationPolicy)
        assert isinstance(scheduler._policies[1], UsageBasedRotationPolicy)
        assert scheduler._key_provider is test_key_provider

    def test_add_remove_policy(self) -> None:
        """Test adding and removing policies."""
        # Create a clean instance
        scheduler = KeyRotationScheduler()
        scheduler._policies = []

        # Add policies
        time_policy = TimeBasedRotationPolicy(max_age_days=5)
        usage_policy = UsageBasedRotationPolicy(max_uses=500)

        scheduler.add_policy(time_policy)
        assert len(scheduler._policies) == 1

        scheduler.add_policy(usage_policy)
        assert len(scheduler._policies) == 2

        # Try to add duplicate - should not add
        scheduler.add_policy(time_policy)
        assert len(scheduler._policies) == 2

        # Remove policy
        scheduler.remove_policy(time_policy)
        assert len(scheduler._policies) == 1
        assert scheduler._policies[0] is usage_policy

    def test_notification_handlers(self) -> None:
        """Test adding and removing notification handlers."""
        # Create a clean instance
        scheduler = KeyRotationScheduler()
        scheduler._notification_handlers = []

        # Add handlers
        async def handler1(event_type: str, details: dict[str, Any]) -> None:
            pass

        async def handler2(event_type: str, details: dict[str, Any]) -> None:
            pass

        scheduler.add_notification_handler(handler1)
        assert len(scheduler._notification_handlers) == 1

        scheduler.add_notification_handler(handler2)
        assert len(scheduler._notification_handlers) == 2

        # Try to add duplicate - should not add
        scheduler.add_notification_handler(handler1)
        assert len(scheduler._notification_handlers) == 2

        # Remove handler
        scheduler.remove_notification_handler(handler1)
        assert len(scheduler._notification_handlers) == 1
        assert scheduler._notification_handlers[0] is handler2

    @pytest.mark.asyncio
    async def test_start_stop(self) -> None:
        """Test starting and stopping the scheduler."""
        # Create a clean instance
        scheduler = KeyRotationScheduler()
        scheduler._running = False
        scheduler._task = None

        # Patch the _scheduler_loop to avoid actual execution
        with patch.object(scheduler, "_scheduler_loop", AsyncMock()) as mock_loop:
            # Start the scheduler
            await scheduler.start()
            assert scheduler._running is True
            assert scheduler._task is not None

            # Start again - should do nothing
            await scheduler.start()

            # Stop the scheduler
            await scheduler.stop()
            assert scheduler._running is False
            assert scheduler._task is None

    @pytest.mark.asyncio
    async def test_check_policies(
        self, mock_secure_value_class: MagicMock, mock_key_history: AsyncMock
    ) -> None:
        """Test checking policies for rotation."""
        # Create a clean instance
        scheduler = KeyRotationScheduler()
        scheduler._history = mock_key_history

        # Create policies
        time_policy = TimeBasedRotationPolicy(max_age_days=5)
        usage_policy = UsageBasedRotationPolicy(max_uses=500)
        scheduler._policies = [time_policy, usage_policy]

        # Mock policy methods
        time_policy.should_rotate = AsyncMock(return_value=False)
        usage_policy.should_rotate = AsyncMock(return_value=True)

        # Mock rotate_key method
        scheduler._rotate_key = AsyncMock()

        # Mock SecureValue
        with patch("uno.config.key_scheduler.SecureValue", mock_secure_value_class):
            # Run policy check
            await scheduler._check_policies()

            # Verify methods were called
            mock_key_history.record_policy_check.assert_called()
            time_policy.should_rotate.assert_called_once()
            usage_policy.should_rotate.assert_called_once()

            # Verify rotate was called with usage policy
            scheduler._rotate_key.assert_called_once()
            scheduler._rotate_key.assert_called_with(cast(str, usage_policy.name))

    @pytest.mark.asyncio
    async def test_rotate_key(
        self, mock_secure_value_class: MagicMock, mock_key_history: AsyncMock
    ) -> None:
        """Test key rotation."""
        # Create a clean instance
        scheduler = KeyRotationScheduler()
        scheduler._history = mock_key_history

        # Mock generate_key method to return predictable values
        scheduler._generate_key = AsyncMock(return_value=("v2", b"new-test-key"))

        # Mock SecureValue
        with (
            patch("uno.config.key_scheduler.SecureValue", mock_secure_value_class),
            patch(
                "uno.config.key_scheduler.setup_key_rotation", AsyncMock()
            ) as mock_setup_rotation,
        ):
            # Mock notification sending
            scheduler._send_notifications = AsyncMock()

            # Rotate key
            await scheduler._rotate_key("TestPolicy")

            # Verify methods were called
            scheduler._generate_key.assert_called_once()
            mock_setup_rotation.assert_called_once_with(
                old_key=b"test-key",
                new_key=b"new-test-key",
                old_version="v1",
                new_version="v2",
            )
            mock_key_history.record_key_rotated.assert_called_once_with(
                "v2",
                RotationReason.SCHEDULED,
                previous_version="v1",
                details={"policy": "TestPolicy"},
            )
            scheduler._send_notifications.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_key(self) -> None:
        """Test key generation."""
        # Create a clean instance
        scheduler = KeyRotationScheduler()

        # Test with custom key provider
        custom_provider = AsyncMock(return_value=("custom-v1", b"custom-key"))
        scheduler._key_provider = custom_provider

        version, key = await scheduler._generate_key()
        assert version == "custom-v1"
        assert key == b"custom-key"
        custom_provider.assert_called_once()

        # Test default implementation
        scheduler._key_provider = None
        version, key = await scheduler._generate_key()
        assert "v" in version  # Should start with v followed by timestamp
        assert len(key) == 32  # Should be 32 bytes

    @pytest.mark.asyncio
    async def test_send_notifications(self) -> None:
        """Test sending notifications."""
        # Create a clean instance
        scheduler = KeyRotationScheduler()

        # Create notification handlers
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        handler3 = AsyncMock(side_effect=Exception("Test error"))

        scheduler._notification_handlers = [handler1, handler2, handler3]

        # Send notifications
        event_details = {"test": "value"}
        await scheduler._send_notifications("test_event", event_details)

        # Verify handlers were called
        handler1.assert_called_once_with("test_event", event_details)
        handler2.assert_called_once_with("test_event", event_details)
        handler3.assert_called_once_with("test_event", event_details)
