# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Key rotation policies for the Uno configuration system.

This module defines policies that determine when encryption keys should be
rotated, supporting time-based, usage-based, and composite policies.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger("uno.config.key_policy")


@runtime_checkable
class KeyRotationPolicyProtocol(Protocol):
    """Protocol defining the interface for key rotation policies.
    
    This protocol is runtime_checkable to support policy registration
    and discovery.
    """
    
    @property
    def name(self) -> str:
        """Get a human-readable name for this policy."""
        ...
    
    @property
    def description(self) -> str:
        """Get a human-readable description of this policy."""
        ...
    
    async def should_rotate(self, key_info: dict[str, Any]) -> bool:
        """Determine if a key should be rotated based on this policy.
        
        Args:
            key_info: Dictionary containing information about the key
                      (creation_time, last_rotation_time, usage_count, etc.)
        
        Returns:
            True if the key should be rotated, False otherwise
        """
        ...


class RotationReason(str, Enum):
    """Reason codes for key rotation events."""
    
    TIME_EXPIRED = "time_expired"        # Key has reached its maximum age
    USAGE_LIMIT = "usage_limit"          # Key has exceeded its usage limit
    MANUAL = "manual"                    # Manual rotation requested
    COMPOSITE = "composite"              # Composite policy triggered
    SCHEDULED = "scheduled"              # Scheduled rotation
    EMERGENCY = "emergency"              # Emergency rotation (potential compromise)
    INITIAL = "initial"                  # Initial key creation
    UNKNOWN = "unknown"                  # Unknown reason


class TimeBasedRotationPolicy:
    """Policy that rotates keys based on age.
    
    This policy triggers rotation when a key reaches a specified age,
    regardless of usage patterns.
    """
    
    def __init__(self, max_age_days: float = 90.0) -> None:
        """Initialize a time-based rotation policy.
        
        Args:
            max_age_days: Maximum age of a key in days before rotation
        """
        self._max_age_days = max_age_days
        self._max_age_seconds = max_age_days * 86400  # Convert to seconds
    
    @property
    def name(self) -> str:
        """Get a human-readable name for this policy."""
        return f"TimeBasedRotation({self._max_age_days}d)"
    
    @property
    def description(self) -> str:
        """Get a human-readable description of this policy."""
        return f"Rotates keys after {self._max_age_days} days"
    
    @property
    def max_age_days(self) -> float:
        """Get the maximum key age in days."""
        return self._max_age_days
    
    async def should_rotate(self, key_info: dict[str, Any]) -> bool:
        """Determine if a key should be rotated based on its age.
        
        Args:
            key_info: Dictionary containing information about the key,
                      including 'creation_time' or 'last_rotation_time'
        
        Returns:
            True if the key should be rotated, False otherwise
        """
        # Get relevant timestamps
        current_time = time.time()
        
        # Use the most recent of creation time or last rotation time
        creation_time = key_info.get("creation_time", 0)
        last_rotation_time = key_info.get("last_rotation_time", 0)
        reference_time = max(creation_time, last_rotation_time)
        
        # If we don't have a valid reference time, don't rotate
        if reference_time <= 0:
            return False
            
        # Calculate age and check against max_age
        age_seconds = current_time - reference_time
        return age_seconds >= self._max_age_seconds
    
    def get_next_rotation_time(self, key_info: dict[str, Any]) -> float:
        """Get the timestamp when the next rotation should occur.
        
        Args:
            key_info: Dictionary containing information about the key
        
        Returns:
            Timestamp when the next rotation should occur
        """
        # Use the most recent of creation time or last rotation time
        creation_time = key_info.get("creation_time", 0)
        last_rotation_time = key_info.get("last_rotation_time", 0)
        reference_time = max(creation_time, last_rotation_time)
        
        return reference_time + self._max_age_seconds


class UsageBasedRotationPolicy:
    """Policy that rotates keys based on usage count.
    
    This policy triggers rotation when a key has been used a specified
    number of times, regardless of age.
    """
    
    def __init__(self, max_uses: int = 1000000) -> None:
        """Initialize a usage-based rotation policy.
        
        Args:
            max_uses: Maximum number of times a key can be used before rotation
        """
        self._max_uses = max_uses
    
    @property
    def name(self) -> str:
        """Get a human-readable name for this policy."""
        return f"UsageBasedRotation({self._max_uses})"
    
    @property
    def description(self) -> str:
        """Get a human-readable description of this policy."""
        return f"Rotates keys after {self._max_uses} uses"
    
    @property
    def max_uses(self) -> int:
        """Get the maximum key uses."""
        return self._max_uses
    
    async def should_rotate(self, key_info: dict[str, Any]) -> bool:
        """Determine if a key should be rotated based on its usage.
        
        Args:
            key_info: Dictionary containing information about the key,
                      including 'usage_count'
        
        Returns:
            True if the key should be rotated, False otherwise
        """
        usage_count = key_info.get("usage_count", 0)
        return usage_count >= self._max_uses
    
    def get_usage_limit_info(self, key_info: dict[str, Any]) -> tuple[int, int]:
        """Get information about usage limit progress.
        
        Args:
            key_info: Dictionary containing information about the key
        
        Returns:
            Tuple of (current_usage, max_usage)
        """
        usage_count = key_info.get("usage_count", 0)
        return (usage_count, self._max_uses)


class CompositeRotationPolicy:
    """Policy that combines multiple other policies.
    
    This policy can be configured to trigger when ANY policy triggers (OR logic)
    or only when ALL policies trigger (AND logic).
    """
    
    def __init__(
        self, 
        policies: list[KeyRotationPolicyProtocol], 
        require_all: bool = False,
        name: str | None = None
    ) -> None:
        """Initialize a composite rotation policy.
        
        Args:
            policies: List of policies to combine
            require_all: If True, all policies must trigger for rotation (AND logic)
                        If False, any policy triggering will cause rotation (OR logic)
            name: Optional custom name for this policy
        """
        if not policies:
            raise ValueError("At least one policy must be provided")
        
        self._policies = list(policies)
        self._require_all = require_all
        self._custom_name = name
    
    @property
    def name(self) -> str:
        """Get a human-readable name for this policy."""
        if self._custom_name:
            return self._custom_name
            
        logic_type = "AND" if self._require_all else "OR"
        policy_names = [p.name for p in self._policies]
        return f"CompositeRotation({logic_type}: {', '.join(policy_names)})"
    
    @property
    def description(self) -> str:
        """Get a human-readable description of this policy."""
        logic_desc = "all" if self._require_all else "any"
        return f"Rotates keys when {logic_desc} of the following policies trigger: " + \
               ", ".join(p.description for p in self._policies)
    
    @property
    def policies(self) -> list[KeyRotationPolicyProtocol]:
        """Get the component policies."""
        return self._policies.copy()
    
    @property
    def require_all(self) -> bool:
        """Check if all policies must trigger for rotation."""
        return self._require_all
    
    async def should_rotate(self, key_info: dict[str, Any]) -> bool:
        """Determine if a key should be rotated based on component policies.
        
        Args:
            key_info: Dictionary containing information about the key
        
        Returns:
            True if the key should be rotated according to policy logic, 
            False otherwise
        """
        results = []
        
        # Check each policy
        for policy in self._policies:
            try:
                result = await policy.should_rotate(key_info)
                results.append(result)
                
                # Short-circuit for OR logic
                if not self._require_all and result:
                    return True
                    
                # Short-circuit for AND logic
                if self._require_all and not result:
                    return False
            except Exception as e:
                logger.warning(f"Error checking policy {policy.name}: {e}")
                # For AND logic, a failed policy is treated as False
                if self._require_all:
                    return False
        
        # If we get here, either:
        # - For AND logic, all policies returned True (or list was empty)
        # - For OR logic, all policies returned False (or list was empty)
        if not results:
            return False
            
        return all(results) if self._require_all else any(results)


class ScheduledRotationPolicy:
    """Policy that rotates keys on a fixed schedule.
    
    This policy triggers rotation at specific times, regardless of key age or usage.
    """
    
    def __init__(
        self,
        schedule_type: str = "daily",
        hour: int = 2,  # 2 AM by default
        minute: int = 0,
        day_of_week: int | None = None,  # 0=Monday, 6=Sunday
        day_of_month: int | None = None,
    ) -> None:
        """Initialize a scheduled rotation policy.
        
        Args:
            schedule_type: One of "daily", "weekly", "monthly"
            hour: Hour of day for rotation (0-23)
            minute: Minute of hour for rotation (0-59)
            day_of_week: Day of week for weekly rotation (0=Monday, 6=Sunday)
            day_of_month: Day of month for monthly rotation (1-31)
        """
        self._schedule_type = schedule_type.lower()
        self._hour = hour
        self._minute = minute
        self._day_of_week = day_of_week
        self._day_of_month = day_of_month
        
        if self._schedule_type not in ("daily", "weekly", "monthly"):
            raise ValueError(f"Invalid schedule type: {schedule_type}")
            
        if self._schedule_type == "weekly" and day_of_week not in range(7):
            raise ValueError("day_of_week must be between 0 (Monday) and 6 (Sunday)")
            
        if self._schedule_type == "monthly" and (day_of_month is None or 
                                              day_of_month < 1 or 
                                              day_of_month > 31):
            raise ValueError("day_of_month must be between 1 and 31")
    
    @property
    def name(self) -> str:
        """Get a human-readable name for this policy."""
        if self._schedule_type == "daily":
            return f"DailyRotation({self._hour:02d}:{self._minute:02d})"
        elif self._schedule_type == "weekly":
            days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            return f"WeeklyRotation({days[self._day_of_week or 0]} {self._hour:02d}:{self._minute:02d})"
        else:  # monthly
            return f"MonthlyRotation(Day {self._day_of_month} {self._hour:02d}:{self._minute:02d})"
    
    @property
    def description(self) -> str:
        """Get a human-readable description of this policy."""
        time_str = f"{self._hour:02d}:{self._minute:02d}"
        
        if self._schedule_type == "daily":
            return f"Rotates keys daily at {time_str}"
        elif self._schedule_type == "weekly":
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            return f"Rotates keys weekly on {days[self._day_of_week or 0]} at {time_str}"
        else:  # monthly
            return f"Rotates keys monthly on day {self._day_of_month} at {time_str}"
    
    async def should_rotate(self, key_info: dict[str, Any]) -> bool:
        """Determine if a key should be rotated based on the schedule.
        
        Args:
            key_info: Dictionary containing information about the key,
                      including 'last_check_time'
        
        Returns:
            True if the key should be rotated, False otherwise
        """
        # Get current time
        now = datetime.now()
        
        # Get last check time
        last_check_time = key_info.get("last_check_time", 0)
        if last_check_time == 0:
            # First check, don't rotate immediately
            return False
            
        # Convert timestamp to datetime
        last_check = datetime.fromtimestamp(last_check_time)
        
        # Create datetime for the scheduled rotation time
        scheduled_time = datetime(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=self._hour,
            minute=self._minute
        )
        
        # Adjust based on schedule type
        if self._schedule_type == "weekly" and self._day_of_week is not None:
            # Adjust day to the scheduled day of week
            days_diff = self._day_of_week - now.weekday()
            if days_diff < 0:
                days_diff += 7  # Move to next week
            scheduled_time = scheduled_time.replace(day=now.day) + timedelta(days=days_diff)
            
        elif self._schedule_type == "monthly" and self._day_of_month is not None:
            # Try to set to the scheduled day of month
            try:
                scheduled_time = scheduled_time.replace(day=self._day_of_month)
            except ValueError:
                # Handle case where the day doesn't exist in current month (e.g., Feb 30)
                # Move to the first day of the next month
                if now.month == 12:
                    next_month = 1
                    next_year = now.year + 1
                else:
                    next_month = now.month + 1
                    next_year = now.year
                    
                scheduled_time = datetime(
                    year=next_year,
                    month=next_month,
                    day=1,
                    hour=self._hour,
                    minute=self._minute
                )
        
        # If the scheduled time is in the past relative to now,
        # and the last check was before the scheduled time,
        # then we should rotate
        return scheduled_time <= now and last_check < scheduled_time
    
    def get_next_scheduled_time(self) -> datetime:
        """Get the next scheduled rotation time.
        
        Returns:
            Datetime object representing the next scheduled rotation
        """
        now = datetime.now()
        
        # Create datetime for today's scheduled time
        scheduled_time = datetime(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=self._hour,
            minute=self._minute
        )
        
        # If today's scheduled time has passed, move to the next occurrence
        if scheduled_time < now:
            if self._schedule_type == "daily":
                scheduled_time += timedelta(days=1)
            elif self._schedule_type == "weekly" and self._day_of_week is not None:
                days_diff = self._day_of_week - now.weekday()
                if days_diff <= 0:  # Today or earlier in the week
                    days_diff += 7  # Move to next week
                scheduled_time += timedelta(days=days_diff)
            elif self._schedule_type == "monthly" and self._day_of_month is not None:
                # Move to the next month
                if now.month == 12:
                    next_month = 1
                    next_year = now.year + 1
                else:
                    next_month = now.month + 1
                    next_year = now.year
                
                # Try to set the correct day in the next month
                try:
                    scheduled_time = scheduled_time.replace(
                        year=next_year, month=next_month, day=self._day_of_month
                    )
                except ValueError:
                    # Handle invalid dates (e.g., Feb 30)
                    # Just use the last day of the month
                    if next_month == 2:
                        # Check for leap year
                        if next_year % 4 == 0 and (next_year % 100 != 0 or next_year % 400 == 0):
                            scheduled_time = scheduled_time.replace(
                                year=next_year, month=next_month, day=29
                            )
                        else:
                            scheduled_time = scheduled_time.replace(
                                year=next_year, month=next_month, day=28
                            )
                    elif next_month in (4, 6, 9, 11):  # 30-day months
                        scheduled_time = scheduled_time.replace(
                            year=next_year, month=next_month, day=30
                        )
                    else:  # 31-day months
                        scheduled_time = scheduled_time.replace(
                            year=next_year, month=next_month, day=31
                        )
        else:
            # For weekly/monthly, if today is the right day but time hasn't passed,
            # use today's scheduled time
            if self._schedule_type == "weekly" and self._day_of_week is not None:
                if now.weekday() != self._day_of_week:
                    # Not the right day of week, calculate days until next occurrence
                    days_diff = self._day_of_week - now.weekday()
                    if days_diff < 0:  # Target day is earlier in the week
                        days_diff += 7  # Move to next week
                    scheduled_time += timedelta(days=days_diff)
            
            elif self._schedule_type == "monthly" and self._day_of_month is not None:
                if now.day != self._day_of_month:
                    # Not the right day of month
                    if now.day < self._day_of_month:
                        # Target day is later this month
                        try:
                            scheduled_time = scheduled_time.replace(day=self._day_of_month)
                        except ValueError:
                            # Invalid date (e.g., Feb 30), move to next month
                            if now.month == 12:
                                scheduled_time = scheduled_time.replace(
                                    year=now.year + 1, month=1, day=self._day_of_month
                                )
                            else:
                                scheduled_time = scheduled_time.replace(
                                    month=now.month + 1, day=self._day_of_month
                                )
                    else:
                        # Target day is in the next month
                        if now.month == 12:
                            next_month = 1
                            next_year = now.year + 1
                        else:
                            next_month = now.month + 1
                            next_year = now.year
                        
                        try:
                            scheduled_time = scheduled_time.replace(
                                year=next_year, month=next_month, day=self._day_of_month
                            )
                        except ValueError:
                            # Handle invalid dates (e.g., Feb 30)
                            if next_month == 2:
                                # Check for leap year
                                if next_year % 4 == 0 and (next_year % 100 != 0 or next_year % 400 == 0):
                                    scheduled_time = scheduled_time.replace(
                                        year=next_year, month=next_month, day=29
                                    )
                                else:
                                    scheduled_time = scheduled_time.replace(
                                        year=next_year, month=next_month, day=28
                                    )
                            elif next_month in (4, 6, 9, 11):  # 30-day months
                                scheduled_time = scheduled_time.replace(
                                    year=next_year, month=next_month, day=30
                                )
                            else:  # 31-day months
                                scheduled_time = scheduled_time.replace(
                                    year=next_year, month=next_month, day=31
                                )
        
        return scheduled_time


# Policy registry for lookup by name
class PolicyRegistry:
    """Registry of available key rotation policies."""
    
    _policies: dict[str, type[KeyRotationPolicyProtocol]] = {}
    
    @classmethod
    def register(cls, policy_type: type[KeyRotationPolicyProtocol], name: str | None = None) -> None:
        """Register a policy type.
        
        Args:
            policy_type: The policy class to register
            name: Optional name to register under (defaults to class name)
        """
        policy_name = name or policy_type.__name__
        cls._policies[policy_name] = policy_type
        logger.debug(f"Registered policy: {policy_name}")
    
    @classmethod
    def get(cls, name: str) -> type[KeyRotationPolicyProtocol] | None:
        """Get a policy type by name.
        
        Args:
            name: Name of the policy type
            
        Returns:
            Policy class or None if not found
        """
        return cls._policies.get(name)
    
    @classmethod
    def list(cls) -> list[str]:
        """List registered policy types.
        
        Returns:
            List of policy names
        """
        return list(cls._policies.keys())


# Register standard policies
PolicyRegistry.register(TimeBasedRotationPolicy)
PolicyRegistry.register(UsageBasedRotationPolicy)
PolicyRegistry.register(CompositeRotationPolicy)
PolicyRegistry.register(ScheduledRotationPolicy)
