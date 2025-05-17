# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""Integration tests for key rotation functionality."""

import asyncio
import os
import time
from typing import Any, Generator, list

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from uno.config.secure import SecureValue, SecureValueHandling
from uno.config.key_rotation import (
    rotate_secure_values,
    setup_key_rotation,
    schedule_key_rotation,
)
from uno.config.key_history import get_key_history
from uno.config.key_policy import RotationReason


@pytest.fixture
def secure_values() -> list[SecureValue[Any]]:
    """Create test secure values for rotation tests."""
    values = [
        SecureValue("secret1", handling=SecureValueHandling.ENCRYPT),
        SecureValue("secret2", handling=SecureValueHandling.ENCRYPT),
        SecureValue("secret3", handling=SecureValueHandling.ENCRYPT),
    ]

    # Mock encryption to avoid actual crypto operations
    for value in values:
        value.rotate_key = AsyncMock()

    return values


@pytest.fixture
async def setup_master_key() -> Generator[None, None, None]:
    """Set up a test master key for rotation tests."""
    # Store original encryption state
    original_keys = (
        SecureValue._encryption_keys.copy()
        if hasattr(SecureValue, "_encryption_keys")
        else {}
    )
    original_version = SecureValue._current_key_version

    # Set up test key
    await SecureValue.setup_encryption(
        master_key=b"test-master-key-for-rotation",
        key_version="v-test",
    )

    yield

    # Restore original state
    SecureValue._encryption_keys = original_keys
    SecureValue._current_key_version = original_version


class TestKeyRotation:
    """Integration tests for key rotation."""

    @pytest.mark.asyncio
    async def test_rotate_secure_values(
        self, secure_values: list[SecureValue[Any]]
    ) -> None:
        """Test rotating multiple secure values."""
        # Patch get_key_history to use a mock
        mock_history = AsyncMock()
        with patch(
            "uno.config.key_rotation.get_key_history", return_value=mock_history
        ):
            # Rotate values - test with parallel mode
            await rotate_secure_values(
                values=secure_values,
                new_key_version="v2",
                parallel=True,
                batch_size=2,
                reason=RotationReason.MANUAL,
            )

            # Verify each value was rotated
            for value in secure_values:
                value.rotate_key.assert_called_once_with("v2")

            # Verify history was recorded
            mock_history.record_key_rotated.assert_called_once()
            mock_history.record_key_used.assert_called()

            # Reset mocks and test with sequential mode
            for value in secure_values:
                value.rotate_key.reset_mock()

            mock_history.record_key_rotated.reset_mock()
            mock_history.record_key_used.reset_mock()

            # Rotate values sequentially
            await rotate_secure_values(
                values=secure_values,
                new_key_version="v3",
                parallel=False,
                reason=RotationReason.MANUAL,
            )

            # Verify each value was rotated
            for value in secure_values:
                value.rotate_key.assert_called_once_with("v3")

            # Verify history was recorded
            mock_history.record_key_rotated.assert_called_once()
            mock_history.record_key_used.assert_called()

    @pytest.mark.asyncio
    async def test_setup_key_rotation(self, setup_master_key: None) -> None:
        """Test setting up key rotation."""
        # Patch get_key_history to use a mock
        mock_history = AsyncMock()
        with patch(
            "uno.config.key_rotation.get_key_history", return_value=mock_history
        ):
            # Set up rotation from old to new key
            old_key = b"old-test-key"
            new_key = b"new-test-key"

            await setup_key_rotation(
                old_key=old_key,
                new_key=new_key,
                old_version="v1",
                new_version="v2",
            )

            # Verify both keys are registered
            assert "v1" in SecureValue._encryption_keys
            assert "v2" in SecureValue._encryption_keys

            # Verify current key is set to new version
            assert SecureValue._current_key_version == "v2"

            # Verify history was recorded
            assert mock_history.record_key_created.call_count == 2
            mock_history.record_key_rotated.assert_called_once_with(
                "v2",
                RotationReason.MANUAL,
                previous_version="v1",
                details={"method": "manual"},
            )

    @pytest.mark.asyncio
    async def test_schedule_key_rotation(self) -> None:
        """Test scheduling key rotation."""
        # Mock the scheduler
        mock_scheduler = AsyncMock()
        mock_scheduler.configure = MagicMock()
        mock_scheduler.start = AsyncMock()

        # Mock policy classes
        mock_time_policy = MagicMock()
        mock_usage_policy = MagicMock()

        with (
            patch(
                "uno.config.key_rotation.get_rotation_scheduler",
                return_value=mock_scheduler,
            ),
            patch(
                "uno.config.key_rotation.TimeBasedRotationPolicy",
                return_value=mock_time_policy,
            ),
            patch(
                "uno.config.key_rotation.UsageBasedRotationPolicy",
                return_value=mock_usage_policy,
            ),
        ):
            # Schedule with default usage policy (None)
            await schedule_key_rotation(
                check_interval_seconds=1800,
                time_based_max_days=30.0,
            )

            # Verify scheduler was configured with time policy only
            mock_scheduler.configure.assert_called_once()
            args, kwargs = mock_scheduler.configure.call_args
            assert len(kwargs["policies"]) == 1
            assert kwargs["policies"][0] is mock_time_policy
            assert kwargs["check_interval"] == 1800

            # Verify scheduler was started
            mock_scheduler.start.assert_called_once()

            # Reset mocks and test with usage policy
            mock_scheduler.configure.reset_mock()
            mock_scheduler.start.reset_mock()

            # Schedule with usage policy
            await schedule_key_rotation(
                check_interval_seconds=1800,
                time_based_max_days=30.0,
                usage_based_max_uses=5000,
            )

            # Verify scheduler was configured with both policies
            mock_scheduler.configure.assert_called_once()
            args, kwargs = mock_scheduler.configure.call_args
            assert len(kwargs["policies"]) == 2
            assert kwargs["check_interval"] == 1800
