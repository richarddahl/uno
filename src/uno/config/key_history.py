# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Key history tracking for the Uno configuration system.

This module provides functionality for tracking key lifecycle events,
usage patterns, and rotation history for audit and policy purposes.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

from uno.config.errors import SecureConfigError, CONFIG_SECURE_ERROR
from uno.config.key_policy import RotationReason

logger = logging.getLogger("uno.config.key_history")


class KeyEvent:
    """Represents a key lifecycle event."""

    def __init__(
        self,
        event_type: str,
        key_version: str,
        timestamp: float | None = None,
        reason: RotationReason | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a key event.

        Args:
            event_type: Type of event (creation, rotation, usage, etc.)
            key_version: Version identifier for the key
            timestamp: Event timestamp (defaults to current time)
            reason: Reason for the event (for rotation events)
            details: Additional details about the event
        """
        self.event_type = event_type
        self.key_version = key_version
        self.timestamp = timestamp or time.time()
        self.reason = reason
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary representation.

        Returns:
            Dictionary representation of the event
        """
        result = {
            "event_type": self.event_type,
            "key_version": self.key_version,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
        }

        if self.reason:
            result["reason"] = self.reason.value

        if self.details:
            result["details"] = self.details

        return result


class KeyHistory:
    """Tracks the history of key lifecycle events.

    This class maintains a history of key-related events, such as
    creation, rotation, and usage for audit and policy purposes.
    """

    # Event types
    EVENT_CREATION = "creation"
    EVENT_ROTATION = "rotation"
    EVENT_USAGE = "usage"
    EVENT_CHECK = "check"

    # Singleton pattern
    _instance: ClassVar[KeyHistory | None] = None

    @classmethod
    def get_instance(cls) -> KeyHistory:
        """Get the singleton instance.

        Returns:
            Singleton KeyHistory instance
        """
        if cls._instance is None:
            cls._instance = KeyHistory()
        return cls._instance

    def __init__(self) -> None:
        """Initialize key history tracking."""
        self._events: list[KeyEvent] = []
        self._version_info: dict[str, dict[str, Any]] = {}
        self._storage_path: Path | None = None
        self._persist_enabled = False

    def configure(
        self,
        storage_path: str | Path | None = None,
        max_events: int = 1000,
        persist: bool = False,
    ) -> None:
        """Configure history tracking.

        Args:
            storage_path: Path to store history logs (if persisting)
            max_events: Maximum number of events to keep in memory
            persist: Whether to persist events to disk
        """
        if storage_path:
            self._storage_path = Path(storage_path)
            os.makedirs(self._storage_path, exist_ok=True)

        self._max_events = max_events
        self._persist_enabled = persist and storage_path is not None

    async def record_event(
        self,
        event_type: str,
        key_version: str,
        reason: RotationReason | None = None,
        details: dict[str, Any] | None = None,
    ) -> KeyEvent:
        """Record a key lifecycle event.

        Args:
            event_type: Type of event (creation, rotation, usage, etc.)
            key_version: Version identifier for the key
            reason: Reason for the event (for rotation events)
            details: Additional details about the event

        Returns:
            The recorded event
        """
        event = KeyEvent(
            event_type=event_type,
            key_version=key_version,
            reason=reason,
            details=details,
        )

        # Add to in-memory history
        self._events.append(event)

        # Trim history if needed
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events :]

        # Update version info
        self._update_version_info(event)

        # Persist event if enabled
        if self._persist_enabled and self._storage_path:
            await self._persist_event(event)

        return event

    def _update_version_info(self, event: KeyEvent) -> None:
        """Update version info based on an event.

        Args:
            event: The event to process
        """
        version = event.key_version
        if version not in self._version_info:
            self._version_info[version] = {
                "creation_time": (
                    event.timestamp if event.event_type == self.EVENT_CREATION else 0
                ),
                "last_rotation_time": 0,
                "last_usage_time": 0,
                "last_check_time": 0,
                "usage_count": 0,
                "rotation_count": 0,
                "active": True,
            }

        info = self._version_info[version]

        # Update specific fields based on event type
        if event.event_type == self.EVENT_CREATION:
            info["creation_time"] = event.timestamp

        elif event.event_type == self.EVENT_ROTATION:
            info["last_rotation_time"] = event.timestamp
            info["rotation_count"] += 1

        elif event.event_type == self.EVENT_USAGE:
            info["last_usage_time"] = event.timestamp
            info["usage_count"] += 1

        elif event.event_type == self.EVENT_CHECK:
            info["last_check_time"] = event.timestamp

    async def _persist_event(self, event: KeyEvent) -> None:
        """Persist an event to disk.

        Args:
            event: The event to persist
        """
        if not self._storage_path:
            return

        try:
            # Create the log file path
            log_file = self._storage_path / f"key_history_{event.key_version}.jsonl"

            # Convert event to JSON line
            event_json = json.dumps(event.to_dict())

            # Append to log file
            import aiofiles

            async with aiofiles.open(log_file, "a") as f:
                await f.write(f"{event_json}\n")

        except Exception as e:
            logger.error(f"Error persisting key event: {e}")

    async def record_key_created(
        self, key_version: str, details: dict[str, Any] | None = None
    ) -> None:
        """Record a key creation event.

        Args:
            key_version: Version identifier for the key
            details: Additional details about the creation
        """
        await self.record_event(
            event_type=self.EVENT_CREATION,
            key_version=key_version,
            reason=RotationReason.INITIAL,
            details=details,
        )
        logger.info(f"Key created: {key_version}")

    async def record_key_rotated(
        self,
        key_version: str,
        reason: RotationReason,
        previous_version: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Record a key rotation event.

        Args:
            key_version: Version identifier for the new key
            reason: Reason for the rotation
            previous_version: Version identifier for the previous key
            details: Additional details about the rotation
        """
        # Prepare details with previous version
        event_details = details or {}
        if previous_version:
            event_details["previous_version"] = previous_version

        await self.record_event(
            event_type=self.EVENT_ROTATION,
            key_version=key_version,
            reason=reason,
            details=event_details,
        )
        logger.info(f"Key rotated: {key_version} (reason: {reason.value})")

        # Mark previous version as inactive
        if previous_version and previous_version in self._version_info:
            self._version_info[previous_version]["active"] = False

    async def record_key_used(
        self, key_version: str, operation: str, details: dict[str, Any] | None = None
    ) -> None:
        """Record a key usage event.

        Args:
            key_version: Version identifier for the key
            operation: The operation the key was used for (encrypt, decrypt, etc.)
            details: Additional details about the usage
        """
        # Prepare details with operation
        event_details = details or {}
        event_details["operation"] = operation

        await self.record_event(
            event_type=self.EVENT_USAGE, key_version=key_version, details=event_details
        )

    async def record_policy_check(
        self,
        key_version: str,
        policy_name: str,
        result: bool,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Record a policy check event.

        Args:
            key_version: Version identifier for the key
            policy_name: Name of the policy checked
            result: Result of the policy check
            details: Additional details about the check
        """
        # Prepare details with policy info
        event_details = details or {}
        event_details["policy"] = policy_name
        event_details["result"] = result

        await self.record_event(
            event_type=self.EVENT_CHECK, key_version=key_version, details=event_details
        )

    def get_version_info(self, key_version: str) -> dict[str, Any]:
        """Get information about a specific key version.

        Args:
            key_version: Version identifier for the key

        Returns:
            Dictionary with key information

        Raises:
            SecureConfigError: If the key version is not found
        """
        if key_version not in self._version_info:
            raise SecureConfigError(
                f"No history for key version: {key_version}",
                code=CONFIG_SECURE_ERROR,
            )
        return self._version_info[key_version].copy()

    def get_active_key_versions(self) -> list[str]:
        """Get a list of active key versions.

        Returns:
            List of active key version identifiers
        """
        return [
            version
            for version, info in self._version_info.items()
            if info.get("active", False)
        ]

    def get_events(
        self,
        key_version: str | None = None,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get key history events, optionally filtered.

        Args:
            key_version: Optional version to filter by
            event_type: Optional event type to filter by
            limit: Maximum number of events to return

        Returns:
            List of event dictionaries
        """
        # Start with all events, newest first
        filtered_events = list(reversed(self._events))

        # Apply filters
        if key_version:
            filtered_events = [
                e for e in filtered_events if e.key_version == key_version
            ]

        if event_type:
            filtered_events = [e for e in filtered_events if e.event_type == event_type]

        # Apply limit
        filtered_events = filtered_events[:limit]

        # Convert to dicts
        return [event.to_dict() for event in filtered_events]

    async def load_history(self) -> None:
        """Load history from storage (if persist is enabled).

        This will merge persisted history with any in-memory events.
        """
        if not self._persist_enabled or not self._storage_path:
            return

        try:
            # Find all history files
            history_files = list(self._storage_path.glob("key_history_*.jsonl"))

            if not history_files:
                logger.info("No key history files found")
                return

            # Clear existing events
            self._events = []
            self._version_info = {}

            # Load each file
            import aiofiles

            for file_path in history_files:
                try:
                    async with aiofiles.open(file_path, "r") as f:
                        content = await f.read()

                    # Process each line as a JSON event
                    for line in content.splitlines():
                        if not line.strip():
                            continue

                        try:
                            event_data = json.loads(line)

                            # Create KeyEvent from the data
                            event = KeyEvent(
                                event_type=event_data["event_type"],
                                key_version=event_data["key_version"],
                                timestamp=event_data["timestamp"],
                                reason=(
                                    RotationReason(event_data["reason"])
                                    if "reason" in event_data
                                    else None
                                ),
                                details=event_data.get("details"),
                            )

                            # Add to in-memory state
                            self._events.append(event)
                            self._update_version_info(event)

                        except (json.JSONDecodeError, KeyError) as e:
                            logger.warning(f"Invalid event in {file_path}: {e}")

                except Exception as e:
                    logger.error(f"Error loading history from {file_path}: {e}")

            # Sort events by timestamp
            self._events.sort(key=lambda e: e.timestamp)

            # Trim to max events
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events :]

            logger.info(f"Loaded {len(self._events)} key history events")

        except Exception as e:
            logger.error(f"Error loading key history: {e}")


# Singleton instance accessor
def get_key_history() -> KeyHistory:
    """Get the key history singleton.

    Returns:
        KeyHistory singleton instance
    """
    return KeyHistory.get_instance()
