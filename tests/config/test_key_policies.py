# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""Tests for key rotation policies."""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, dict

import pytest

from uno.config.key_policy import (
    TimeBasedRotationPolicy,
    UsageBasedRotationPolicy,
    CompositeRotationPolicy,
    ScheduledRotationPolicy,
    RotationReason,
    PolicyRegistry,
)


class TestTimeBasedPolicy:
    """Tests for TimeBasedRotationPolicy."""

    @pytest.mark.asyncio
    async def test_should_rotate_when_expired(self) -> None:
        """Test that policy triggers rotation when time has expired."""
        # Setup
        policy = TimeBasedRotationPolicy(max_age_days=10)

        # Current time is 11 days after last rotation
        current_time = time.time()
        key_info = {
            "creation_time": current_time - 12 * 86400,  # 12 days ago
            "last_rotation_time": current_time - 11 * 86400,  # 11 days ago
        }

        # Verify
        should_rotate = await policy.should_rotate(key_info)
        assert should_rotate is True

    @pytest.mark.asyncio
    async def test_should_not_rotate_when_not_expired(self) -> None:
        """Test that policy doesn't trigger rotation when time hasn't expired."""
        # Setup
        policy = TimeBasedRotationPolicy(max_age_days=10)

        # Current time is 9 days after last rotation
        current_time = time.time()
        key_info = {
            "creation_time": current_time - 15 * 86400,  # 15 days ago
            "last_rotation_time": current_time - 9 * 86400,  # 9 days ago
        }

        # Verify
        should_rotate = await policy.should_rotate(key_info)
        assert should_rotate is False

    @pytest.mark.asyncio
    async def test_no_rotation_history(self) -> None:
        """Test handling of keys with no rotation history."""
        # Setup
        policy = TimeBasedRotationPolicy(max_age_days=10)

        # Key created 11 days ago, no rotations
        current_time = time.time()
        key_info = {
            "creation_time": current_time - 11 * 86400,  # 11 days ago
            "last_rotation_time": 0,  # Never rotated
        }

        # Verify - should use creation_time
        should_rotate = await policy.should_rotate(key_info)
        assert should_rotate is True

    def test_get_next_rotation_time(self) -> None:
        """Test calculation of next rotation time."""
        # Setup
        policy = TimeBasedRotationPolicy(max_age_days=10)
        current_time = time.time()
        key_info = {
            "creation_time": current_time - 5 * 86400,  # 5 days ago
            "last_rotation_time": 0,
        }

        # Get next rotation time
        next_time = policy.get_next_rotation_time(key_info)

        # Verify - should be creation_time + 10 days
        expected_time = key_info["creation_time"] + 10 * 86400
        assert abs(next_time - expected_time) < 1  # Allow small float imprecision


class TestUsageBasedPolicy:
    """Tests for UsageBasedRotationPolicy."""

    @pytest.mark.asyncio
    async def test_should_rotate_when_usage_limit_reached(self) -> None:
        """Test that policy triggers rotation when usage limit is reached."""
        # Setup
        policy = UsageBasedRotationPolicy(max_uses=1000)

        key_info = {"usage_count": 1001}  # Over the limit

        # Verify
        should_rotate = await policy.should_rotate(key_info)
        assert should_rotate is True

    @pytest.mark.asyncio
    async def test_should_not_rotate_when_under_usage_limit(self) -> None:
        """Test that policy doesn't trigger rotation when under usage limit."""
        # Setup
        policy = UsageBasedRotationPolicy(max_uses=1000)

        key_info = {"usage_count": 999}  # Under the limit

        # Verify
        should_rotate = await policy.should_rotate(key_info)
        assert should_rotate is False

    @pytest.mark.asyncio
    async def test_no_usage_count(self) -> None:
        """Test handling of keys with no usage count."""
        # Setup
        policy = UsageBasedRotationPolicy(max_uses=1000)

        key_info = {}  # No usage count

        # Verify - should default to 0
        should_rotate = await policy.should_rotate(key_info)
        assert should_rotate is False

    def test_get_usage_limit_info(self) -> None:
        """Test getting usage limit information."""
        # Setup
        policy = UsageBasedRotationPolicy(max_uses=1000)

        key_info = {"usage_count": 500}

        # Get usage info
        current, max_uses = policy.get_usage_limit_info(key_info)

        # Verify
        assert current == 500
        assert max_uses == 1000


class TestCompositePolicy:
    """Tests for CompositeRotationPolicy."""

    @pytest.mark.asyncio
    async def test_or_logic_any_true(self) -> None:
        """Test OR logic (require_all=False) when any policy is true."""
        # Setup - create two policies, one true and one false
        time_policy = TimeBasedRotationPolicy(max_age_days=10)
        usage_policy = UsageBasedRotationPolicy(max_uses=1000)

        # Create composite with OR logic (default)
        composite = CompositeRotationPolicy([time_policy, usage_policy])

        # Key info - old enough but under usage limit
        current_time = time.time()
        key_info = {
            "creation_time": current_time - 11 * 86400,  # 11 days ago
            "usage_count": 500,  # Under limit
        }

        # Verify - should be True because time policy is True
        should_rotate = await composite.should_rotate(key_info)
        assert should_rotate is True

    @pytest.mark.asyncio
    async def test_or_logic_all_false(self) -> None:
        """Test OR logic (require_all=False) when all policies are false."""
        # Setup - create two policies, both false
        time_policy = TimeBasedRotationPolicy(max_age_days=10)
        usage_policy = UsageBasedRotationPolicy(max_uses=1000)

        # Create composite with OR logic (default)
        composite = CompositeRotationPolicy([time_policy, usage_policy])

        # Key info - not old enough and under usage limit
        current_time = time.time()
        key_info = {
            "creation_time": current_time - 5 * 86400,  # 5 days ago
            "usage_count": 500,  # Under limit
        }

        # Verify - should be False because both policies are False
        should_rotate = await composite.should_rotate(key_info)
        assert should_rotate is False

    @pytest.mark.asyncio
    async def test_and_logic_all_true(self) -> None:
        """Test AND logic (require_all=True) when all policies are true."""
        # Setup - create two policies, both true
        time_policy = TimeBasedRotationPolicy(max_age_days=10)
        usage_policy = UsageBasedRotationPolicy(max_uses=1000)

        # Create composite with AND logic
        composite = CompositeRotationPolicy(
            [time_policy, usage_policy], require_all=True
        )

        # Key info - old enough and over usage limit
        current_time = time.time()
        key_info = {
            "creation_time": current_time - 11 * 86400,  # 11 days ago
            "usage_count": 1001,  # Over limit
        }

        # Verify - should be True because both policies are True
        should_rotate = await composite.should_rotate(key_info)
        assert should_rotate is True

    @pytest.mark.asyncio
    async def test_and_logic_any_false(self) -> None:
        """Test AND logic (require_all=True) when any policy is false."""
        # Setup - create two policies, one true and one false
        time_policy = TimeBasedRotationPolicy(max_age_days=10)
        usage_policy = UsageBasedRotationPolicy(max_uses=1000)

        # Create composite with AND logic
        composite = CompositeRotationPolicy(
            [time_policy, usage_policy], require_all=True
        )

        # Key info - old enough but under usage limit
        current_time = time.time()
        key_info = {
            "creation_time": current_time - 11 * 86400,  # 11 days ago
            "usage_count": 500,  # Under limit
        }

        # Verify - should be False because usage policy is False
        should_rotate = await composite.should_rotate(key_info)
        assert should_rotate is False

    @pytest.mark.asyncio
    async def test_error_handling(self) -> None:
        """Test error handling in policy evaluation."""

        # Setup - create a mock policy that raises an exception
        class FailingPolicy:
            @property
            def name(self) -> str:
                return "FailingPolicy"

            @property
            def description(self) -> str:
                return "Always fails"

            async def should_rotate(self, key_info: dict[str, Any]) -> bool:
                raise ValueError("Simulated failure")

        # Create a valid policy
        time_policy = TimeBasedRotationPolicy(max_age_days=10)

        # For OR logic, if one policy fails but another is True, result should be True
        composite_or = CompositeRotationPolicy([FailingPolicy(), time_policy])

        # For AND logic, if any policy fails, result should be False
        composite_and = CompositeRotationPolicy(
            [FailingPolicy(), time_policy], require_all=True
        )

        # Key info - old enough to trigger time policy
        current_time = time.time()
        key_info = {
            "creation_time": current_time - 11 * 86400,  # 11 days ago
        }

        # Verify OR logic - should be True because time policy is True
        should_rotate_or = await composite_or.should_rotate(key_info)
        assert should_rotate_or is True

        # Verify AND logic - should be False because one policy failed
        should_rotate_and = await composite_and.should_rotate(key_info)
        assert should_rotate_and is False


class TestScheduledPolicy:
    """Tests for ScheduledRotationPolicy."""

    @pytest.mark.asyncio
    async def test_daily_rotation(self) -> None:
        """Test daily scheduled rotation."""
        # Get current hour and set policy to rotate 1 hour ago
        now = datetime.now()
        hour_ago = (now - timedelta(hours=1)).hour

        # Create policy that rotates daily at 1 hour ago
        policy = ScheduledRotationPolicy(schedule_type="daily", hour=hour_ago, minute=0)

        # Key info - checked yesterday
        yesterday = now - timedelta(days=1)
        key_info = {"last_check_time": yesterday.timestamp()}

        # Should rotate because scheduled time has passed since last check
        should_rotate = await policy.should_rotate(key_info)
        assert should_rotate is True

    @pytest.mark.asyncio
    async def test_not_yet_scheduled(self) -> None:
        """Test when scheduled time hasn't arrived yet."""
        # Get current hour and set policy to rotate 1 hour from now
        now = datetime.now()
        hour_from_now = (now + timedelta(hours=1)).hour

        # Create policy that rotates daily at 1 hour from now
        policy = ScheduledRotationPolicy(
            schedule_type="daily", hour=hour_from_now, minute=0
        )

        # Key info - checked recently
        key_info = {"last_check_time": now.timestamp() - 3600}  # 1 hour ago

        # Should not rotate because scheduled time hasn't arrived yet
        should_rotate = await policy.should_rotate(key_info)
        assert should_rotate is False

    @pytest.mark.asyncio
    async def test_weekly_rotation(self) -> None:
        """Test weekly scheduled rotation."""
        # Get current day and time
        now = datetime.now()

        # Use yesterday's day of week for the policy
        yesterday = now - timedelta(days=1)
        yesterday_dow = yesterday.weekday()  # 0=Monday, 6=Sunday

        # Create policy that rotates weekly on yesterday's day
        policy = ScheduledRotationPolicy(
            schedule_type="weekly", day_of_week=yesterday_dow, hour=0, minute=0
        )

        # Key info - checked 8 days ago (before last scheduled rotation)
        eight_days_ago = now - timedelta(days=8)
        key_info = {"last_check_time": eight_days_ago.timestamp()}

        # Should rotate because weekly schedule has passed
        should_rotate = await policy.should_rotate(key_info)
        assert should_rotate is True

    @pytest.mark.asyncio
    async def test_monthly_rotation(self) -> None:
        """Test monthly scheduled rotation."""
        # Get current date
        now = datetime.now()

        # Use a day that's definitely in the past this month
        past_day = min(now.day - 1, 28)  # Ensure it works for all months
        if past_day <= 0:
            # Handle case where we're on the 1st of the month
            past_day = 28

        # Create policy that rotates monthly on the past day
        policy = ScheduledRotationPolicy(
            schedule_type="monthly", day_of_month=past_day, hour=0, minute=0
        )

        # Key info - checked 40 days ago (before last scheduled rotation)
        days_ago = now - timedelta(days=40)
        key_info = {"last_check_time": days_ago.timestamp()}

        # Should rotate because monthly schedule has passed
        should_rotate = await policy.should_rotate(key_info)
        assert should_rotate is True

    def test_get_next_scheduled_time(self) -> None:
        """Test calculation of next scheduled rotation time."""
        # Create policy for daily rotation at midnight
        policy = ScheduledRotationPolicy(schedule_type="daily", hour=0, minute=0)

        # Get next scheduled time
        next_time = policy.get_next_scheduled_time()

        # Verify it's a future date at midnight
        now = datetime.now()
        assert next_time > now
        assert next_time.hour == 0
        assert next_time.minute == 0


class TestPolicyRegistry:
    """Tests for PolicyRegistry."""

    def test_register_and_get_policy(self) -> None:
        """Test registering and retrieving policies."""

        # Create a custom policy class
        class CustomPolicy:
            @property
            def name(self) -> str:
                return "CustomPolicy"

            @property
            def description(self) -> str:
                return "Custom policy for testing"

            async def should_rotate(self, key_info: dict[str, Any]) -> bool:
                return True

        # Register the policy
        PolicyRegistry.register(CustomPolicy, "custom_test_policy")

        # Retrieve the policy
        policy_class = PolicyRegistry.get("custom_test_policy")

        # Verify
        assert policy_class is not None
        assert policy_class is CustomPolicy

    def test_list_policies(self) -> None:
        """Test listing registered policies."""
        # Get list of registered policies
        policies = PolicyRegistry.list()

        # Verify standard policies are registered
        assert "TimeBasedRotationPolicy" in policies
        assert "UsageBasedRotationPolicy" in policies
        assert "CompositeRotationPolicy" in policies
        assert "ScheduledRotationPolicy" in policies
