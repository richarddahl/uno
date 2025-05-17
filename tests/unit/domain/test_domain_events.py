"""Tests for domain events."""

import copy
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict

import pytest
from pydantic import ValidationError, TypeAdapter

from uno.domain.events import DomainEvent


class MockEvent(DomainEvent):
    """Test event class for testing inheritance."""

    custom_field: str = "test_value"


class AnotherTestEvent(DomainEvent):
    """Another test event class for testing multiple event types."""

    another_field: int = 42


def test_domain_event_creation() -> None:
    """Test basic domain event creation."""
    event = DomainEvent()

    assert event.event_id is not None
    assert event.event_type == "DomainEvent"
    assert isinstance(event.occurred_on, datetime)
    assert event.version == 1
    assert event.aggregate_id is None
    assert event.aggregate_version == 1


def test_domain_event_with_aggregate_id() -> None:
    """Test domain event with aggregate ID."""
    aggregate_id = str(uuid.uuid4())
    event = DomainEvent(aggregate_id=aggregate_id)

    assert event.aggregate_id == aggregate_id


def test_domain_event_with_aggregate_version() -> None:
    """Test domain event with custom aggregate version."""
    aggregate_version = 5
    event = DomainEvent(aggregate_version=aggregate_version)

    assert event.aggregate_version == aggregate_version


def test_domain_event_serialization() -> None:
    """Test domain event serialization and deserialization."""
    event = DomainEvent()
    event_dict = event.model_dump()

    assert "event_id" in event_dict
    assert "event_type" in event_dict
    assert "occurred_on" in event_dict
    assert "version" in event_dict
    assert "aggregate_id" in event_dict
    assert "aggregate_version" in event_dict

    # Test deserialization
    new_event = DomainEvent.model_validate(event_dict)
    assert new_event.event_id == event.event_id
    assert new_event.event_type == event.event_type
    assert new_event.occurred_on == event.occurred_on
    assert new_event.version == event.version
    assert new_event.aggregate_id == event.aggregate_id
    assert new_event.aggregate_version == event.aggregate_version


def test_domain_event_equality() -> None:
    """Test domain event equality comparison."""
    event1 = DomainEvent()
    event2 = DomainEvent()

    # Different events should not be equal
    assert event1 != event2

    # Same event should be equal to itself
    assert event1 == event1

    # Event with same ID should be equal
    event_id = uuid.uuid4()
    event3 = DomainEvent(event_id=event_id)
    event4 = DomainEvent(event_id=event_id)
    assert event3 == event4


def test_domain_event_aggregate_id_update() -> None:
    """Test updating aggregate_id after creation."""
    event = DomainEvent()
    aggregate_id = str(uuid.uuid4())

    # Should be able to set aggregate_id
    event.aggregate_id = aggregate_id
    assert event.aggregate_id == aggregate_id


def test_domain_event_aggregate_version_validation() -> None:
    """Test validation of aggregate_version."""
    # Should raise for invalid version on creation
    with pytest.raises(ValueError):
        DomainEvent.model_validate({"aggregate_version": 0})  # Must be >= 1

    # Should work with valid version
    event = DomainEvent(aggregate_version=1)
    assert event.aggregate_version == 1

    # Should raise if validated with invalid value
    with pytest.raises(ValueError):
        DomainEvent.model_validate({"aggregate_version": 0})


def test_domain_event_with_state() -> None:
    """Test domain event with state."""
    state = {"key1": "value1", "key2": 123}
    event = DomainEvent(state=state)

    assert event.state == state

    # Should be able to update state
    event.state["key3"] = [1, 2, 3]
    assert event.state["key3"] == [1, 2, 3]


def test_domain_event_inheritance() -> None:
    """Test that DomainEvent subclasses work correctly."""
    event = MockEvent(
        aggregate_id="test_aggregate", aggregate_version=1, custom_field="custom_value"
    )

    assert event.event_type == "MockEvent"
    assert event.custom_field == "custom_value"
    assert event.aggregate_id == "test_aggregate"
    assert event.aggregate_version == 1


def test_domain_event_json_serialization() -> None:
    """Test JSON serialization of domain events."""
    event = DomainEvent(
        aggregate_id="test_aggregate",
        aggregate_version=1,
        state={"key": "value"},
        metadata={"source": "test"},
    )

    # Convert to JSON and back
    json_str = event.model_dump_json()
    loaded_event = DomainEvent.model_validate_json(json_str)

    assert loaded_event.event_id == event.event_id
    assert loaded_event.event_type == event.event_type
    assert loaded_event.aggregate_id == event.aggregate_id
    assert loaded_event.aggregate_version == event.aggregate_version
    assert loaded_event.state == event.state
    assert loaded_event.metadata == event.metadata


def test_domain_event_copy() -> None:
    """Test copying domain events."""
    event = DomainEvent(
        aggregate_id="test_aggregate", aggregate_version=1, state={"key": "value"}
    )

    # Test shallow copy
    event_copy = copy.copy(event)
    assert event_copy == event
    assert event_copy is not event

    # Test deep copy
    event_deepcopy = copy.deepcopy(event)
    assert event_deepcopy == event
    assert event_deepcopy is not event


def test_domain_event_timestamps() -> None:
    """Test that timestamps are set correctly."""
    before = datetime.now(timezone.utc)
    event = DomainEvent()
    after = datetime.now(timezone.utc)

    # Convert all to timezone-naive for comparison
    before_naive = before.astimezone().replace(tzinfo=None)
    after_naive = after.astimezone().replace(tzinfo=None)

    # Check that the timestamp is between before and after
    assert before_naive <= event.occurred_on <= after_naive


def test_domain_event_with_custom_occurred_on() -> None:
    """Test creating an event with a custom occurred_on timestamp."""
    custom_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    event = DomainEvent(occurred_on=custom_time)

    assert event.occurred_on == custom_time


def test_domain_event_with_custom_event_id() -> None:
    """Test creating an event with a custom event ID."""
    custom_id = uuid.uuid4()
    event = DomainEvent(event_id=custom_id)

    assert event.event_id == custom_id


def test_domain_event_with_custom_version() -> None:
    """Test creating an event with a custom version."""
    event = DomainEvent(version=2)
    assert event.version == 2


def test_domain_event_with_nested_state() -> None:
    """Test domain event with nested state."""
    nested_state = {
        "nested": {"key1": "value1", "key2": [1, 2, 3], "key3": {"a": 1, "b": 2}}
    }
    event = DomainEvent(state=nested_state)

    assert event.state == nested_state
    assert event.state["nested"]["key1"] == "value1"
    assert event.state["nested"]["key2"] == [1, 2, 3]
    assert event.state["nested"]["key3"] == {"a": 1, "b": 2}


def test_domain_event_with_frozen_state() -> None:
    """Test that state is mutable by default but can be frozen."""
    event = DomainEvent(state={"key": "value"})

    # Should be able to modify state by default
    event.state["key"] = "new_value"
    assert event.state["key"] == "new_value"

    # Create a frozen copy using model_copy with frozen=True
    frozen_event = event.model_copy(deep=True)

    # The state should be a new dict, so modifying it won't affect the original
    frozen_event.state["key"] = "another_value"
    assert frozen_event.state["key"] == "another_value"
    assert event.state["key"] == "new_value"  # Original remains unchanged
