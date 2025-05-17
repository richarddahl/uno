# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""Tests for key history tracking."""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Generator

import pytest

from uno.config.key_history import KeyEvent, KeyHistory, get_key_history
from uno.config.key_policy import RotationReason


@pytest.fixture
def temp_history_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary directory for key history storage."""
    history_dir = tmp_path / "key_history"
    history_dir.mkdir()
    yield history_dir


class TestKeyEvent:
    """Tests for KeyEvent class."""

    def test_init_with_defaults(self) -> None:
        """Test initialization with defaults."""
        event = KeyEvent(
            event_type="test",
            key_version="v1",
        )

        assert event.event_type == "test"
        assert event.key_version == "v1"
        assert event.timestamp > 0  # Should have a timestamp
        assert event.reason is None
        assert event.details == {}

    def test_init_with_custom_values(self) -> None:
        """Test initialization with custom values."""
        custom_time = time.time() - 3600  # 1 hour ago
        custom_details = {"test": "value"}

        event = KeyEvent(
            event_type="rotation",
            key_version="v2",
            timestamp=custom_time,
            reason=RotationReason.SCHEDULED,
            details=custom_details,
        )

        assert event.event_type == "rotation"
        assert event.key_version == "v2"
        assert event.timestamp == custom_time
        assert event.reason == RotationReason.SCHEDULED
        assert event.details == custom_details

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        custom_time = time.time()
        custom_details = {"test": "value"}

        event = KeyEvent(
            event_type="rotation",
            key_version="v2",
            timestamp=custom_time,
            reason=RotationReason.MANUAL,
            details=custom_details,
        )

        event_dict = event.to_dict()

        assert event_dict["event_type"] == "rotation"
        assert event_dict["key_version"] == "v2"
        assert event_dict["timestamp"] == custom_time
        assert "datetime" in event_dict  # Should include ISO format datetime
        assert event_dict["reason"] == RotationReason.MANUAL.value
        assert event_dict["details"] == custom_details


class TestKeyHistory:
    """Tests for KeyHistory class."""

    @pytest.mark.asyncio
    async def test_singleton_pattern(self) -> None:
        """Test that KeyHistory uses the singleton pattern."""
        # Get two instances
        history1 = KeyHistory.get_instance()
        history2 = KeyHistory.get_instance()

        # Should be the same object
        assert history1 is history2

        # get_key_history should return the same instance
        history3 = get_key_history()
        assert history1 is history3

    @pytest.mark.asyncio
    async def test_record_event(self) -> None:
        """Test recording events."""
        # Get a clean instance
        history = KeyHistory()
        history._events = []

        # Record an event
        event = await history.record_event(
            event_type="test",
            key_version="v1",
            reason=RotationReason.INITIAL,
            details={"test": "value"},
        )

        # Verify event was recorded
        assert len(history._events) == 1
        assert history._events[0] is event
        assert event.event_type == "test"
        assert event.key_version == "v1"
        assert event.reason == RotationReason.INITIAL
        assert event.details == {"test": "value"}

    @pytest.mark.asyncio
    async def test_update_version_info(self) -> None:
        """Test that version info is updated when events are recorded."""
        # Get a clean instance
        history = KeyHistory()
        history._events = []
        history._version_info = {}

        # Record creation event
        creation_time = time.time() - 86400  # 1 day ago
        await history.record_event(
            event_type=KeyHistory.EVENT_CREATION,
            key_version="v1",
            reason=RotationReason.INITIAL,
            details={"creation_time": creation_time},
        )

        # Verify version info was created
        assert "v1" in history._version_info
        assert history._version_info["v1"]["creation_time"] > 0
        assert history._version_info["v1"]["active"] is True

        # Record usage event
        await history.record_event(
            event_type=KeyHistory.EVENT_USAGE,
            key_version="v1",
            details={"operation": "encrypt"},
        )

        # Verify usage count was incremented
        assert history._version_info["v1"]["usage_count"] == 1
        assert history._version_info["v1"]["last_usage_time"] > 0

        # Record rotation event
        await history.record_event(
            event_type=KeyHistory.EVENT_ROTATION,
            key_version="v2",
            reason=RotationReason.SCHEDULED,
            details={"previous_version": "v1"},
        )

        # Verify v2 was created and rotation count incremented
        assert "v2" in history._version_info
        assert history._version_info["v2"]["active"] is True
        assert history._version_info["v1"]["active"] is False  # Marked inactive

    @pytest.mark.asyncio
    async def test_persistence(self, temp_history_dir: Path) -> None:
        """Test event persistence to disk."""
        # Get a clean instance and configure persistence
        history = KeyHistory()
        history._events = []
        history._version_info = {}
        history.configure(storage_path=temp_history_dir, persist=True)

        # Record events
        await history.record_key_created("v1", {"method": "test"})
        await history.record_key_used("v1", "encrypt", {"data_size": 100})
        await history.record_key_rotated(
            "v2", RotationReason.MANUAL, "v1", {"method": "test"}
        )

        # Verify files were created
        v1_file = temp_history_dir / "key_history_v1.jsonl"
        v2_file = temp_history_dir / "key_history_v2.jsonl"

        assert v1_file.exists()
        assert v2_file.exists()

        # Check file contents
        v1_content = v1_file.read_text()
        v2_content = v2_file.read_text()

        assert "creation" in v1_content
        assert "usage" in v1_content
        assert "rotation" in v2_content

    @pytest.mark.asyncio
    async def test_load_history(self, temp_history_dir: Path) -> None:
        """Test loading history from disk."""
        # Create a log file directly
        v1_file = temp_history_dir / "key_history_v1.jsonl"

        events = [
            {
                "event_type": "creation",
                "key_version": "v1",
                "timestamp": time.time() - 86400,
                "datetime": (datetime.now() - timedelta(days=1)).isoformat(),
                "reason": "initial",
                "details": {"method": "test"},
            },
            {
                "event_type": "usage",
                "key_version": "v1",
                "timestamp": time.time() - 3600,
                "datetime": (datetime.now() - timedelta(hours=1)).isoformat(),
                "details": {"operation": "encrypt"},
            },
        ]

        with open(v1_file, "w") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")

        # Configure history and load
        history = KeyHistory()
        history._events = []
        history._version_info = {}
        history.configure(storage_path=temp_history_dir, persist=True)

        await history.load_history()

        # Verify events were loaded
        assert len(history._events) == 2
        assert history._events[0].event_type == "creation"
        assert history._events[1].event_type == "usage"

        # Verify version info was updated
        assert "v1" in history._version_info
        assert history._version_info["v1"]["creation_time"] > 0
        assert history._version_info["v1"]["usage_count"] == 1

    @pytest.mark.asyncio
    async def test_get_version_info(self) -> None:
        """Test getting version info."""
        # Get a clean instance
        history = KeyHistory()
        history._events = []
        history._version_info = {
            "v1": {
                "creation_time": time.time() - 86400,
                "last_rotation_time": 0,
                "usage_count": 5,
                "active": True,
            }
        }

        # Get info for v1
        info = history.get_version_info("v1")

        # Verify
        assert info["creation_time"] > 0
        assert info["usage_count"] == 5
        assert info["active"] is True

        # Try to get info for non-existent version
        with pytest.raises(Exception):
            history.get_version_info("not_exists")

    @pytest.mark.asyncio
    async def test_get_active_key_versions(self) -> None:
        """Test getting active key versions."""
        # Get a clean instance
        history = KeyHistory()
        history._version_info = {
            "v1": {"active": False},
            "v2": {"active": True},
            "v3": {"active": True},
            "v4": {"active": False},
        }

        # Get active versions
        active = history.get_active_key_versions()

        # Verify
        assert len(active) == 2
        assert "v2" in active
        assert "v3" in active
        assert "v1" not in active
        assert "v4" not in active

    @pytest.mark.asyncio
    async def test_get_events(self) -> None:
        """Test getting events with filters."""
        # Get a clean instance
        history = KeyHistory()

        # Create some events
        event1 = KeyEvent("creation", "v1", time.time() - 3600)
        event2 = KeyEvent("usage", "v1", time.time() - 1800)
        event3 = KeyEvent("rotation", "v2", time.time() - 900, RotationReason.MANUAL)
        event4 = KeyEvent("usage", "v2", time.time())

        history._events = [event1, event2, event3, event4]

        # Get all events
        all_events = history.get_events()
        assert len(all_events) == 4

        # Filter by key version
        v1_events = history.get_events(key_version="v1")
        assert len(v1_events) == 2
        assert v1_events[0]["key_version"] == "v1"
        assert v1_events[1]["key_version"] == "v1"

        # Filter by event type
        usage_events = history.get_events(event_type="usage")
        assert len(usage_events) == 2
        assert usage_events[0]["event_type"] == "usage"
        assert usage_events[1]["event_type"] == "usage"

        # Filter by both
        v2_usage = history.get_events(key_version="v2", event_type="usage")
        assert len(v2_usage) == 1
        assert v2_usage[0]["key_version"] == "v2"
        assert v2_usage[0]["event_type"] == "usage"

        # Test limit
        limited = history.get_events(limit=2)
        assert len(limited) == 2
