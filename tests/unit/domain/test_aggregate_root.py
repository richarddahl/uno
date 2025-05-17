"""Tests for the AggregateRoot base class."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Any, ClassVar, Dict, List, Optional, Type, cast
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, Field

from uno.domain.aggregate import AggregateRoot
from uno.domain.events import DomainEvent


# Test Events
class MockEvent(DomainEvent):
    """A test event for aggregate testing."""

    value: int

    def __init__(self, **data: Any) -> None:
        # Ensure aggregate_id is a string
        if "aggregate_id" in data and isinstance(data["aggregate_id"], UUID):
            data["aggregate_id"] = str(data["aggregate_id"])
        super().__init__(**data)


class AnotherTestEvent(DomainEvent):
    """Another test event for aggregate testing."""

    name: str
    amount: float

    def __init__(self, **data: Any) -> None:
        # Ensure aggregate_id is a string
        if "aggregate_id" in data and isinstance(data["aggregate_id"], UUID):
            data["aggregate_id"] = str(data["aggregate_id"])
        super().__init__(**data)


# Test Aggregate
class MockAggregate(AggregateRoot[DomainEvent]):
    """A test aggregate for testing AggregateRoot functionality."""

    counter: int = 0
    name: str = ""
    last_event: Optional[DomainEvent] = None
    _processed_events: List[DomainEvent]

    def __init__(self, **data: Any) -> None:
        self._processed_events = []
        super().__init__(**data)

    def increment(self, amount: int = 1) -> None:
        """Increment the counter by the given amount."""
        self._raise_event(
            MockEvent(
                value=amount,
                aggregate_id=str(self.id),  # Convert UUID to string for the event
            )
        )

    def set_name(self, name: str) -> None:
        """Set the name of the aggregate."""
        self._raise_event(
            AnotherTestEvent(
                name=name,
                amount=len(name),
                aggregate_id=str(self.id),  # Convert UUID to string for the event
            )
        )

    def on_TestEvent(self, event: MockEvent) -> None:
        """Handle MockEvent."""
        self.counter += event.value
        self.last_event = event
        self._processed_events.append(event)

    def on_AnotherTestEvent(self, event: AnotherTestEvent) -> None:
        """Handle AnotherTestEvent."""
        self.name = event.name
        self.last_event = event
        self._processed_events.append(event)

    def _get_state(self) -> Dict[str, Any]:
        """Get the current state for snapshots."""
        last_event_data = None
        if self.last_event:
            last_event_data = {
                "event_type": self.last_event.__class__.__name__,
                "value": getattr(self.last_event, "value", None),
                "name": getattr(self.last_event, "name", None),
                "amount": getattr(self.last_event, "amount", None),
                "aggregate_id": str(self.id),
                "aggregate_version": self.version,
                "occurred_on": getattr(self.last_event, "occurred_on", None),
                "version": getattr(self.last_event, "version", 1),
            }

        return {
            "counter": self.counter,
            "name": self.name,
            "last_event": last_event_data,
        }

    @classmethod
    def from_snapshot(cls, snapshot: Dict[str, Any], **kwargs: Any) -> "MockAggregate":
        """Create an aggregate from a snapshot."""
        obj = cls(**kwargs)
        if "counter" in snapshot:
            obj.counter = snapshot["counter"]
        if "name" in snapshot:
            obj.name = snapshot["name"]

        if "last_event" in snapshot and snapshot["last_event"]:
            # Restore the last event if needed
            event_data = snapshot["last_event"]
            if event_data.get("event_type") == "MockEvent":
                obj.last_event = MockEvent(
                    value=event_data.get("value", 0),
                    aggregate_id=event_data.get("aggregate_id", str(obj.id)),
                    aggregate_version=event_data.get("aggregate_version", 1),
                    version=event_data.get("version", 1),
                )
            elif event_data.get("event_type") == "AnotherTestEvent":
                obj.last_event = AnotherTestEvent(
                    name=event_data.get("name", ""),
                    amount=event_data.get("amount", 0.0),
                    aggregate_id=event_data.get("aggregate_id", str(obj.id)),
                    aggregate_version=event_data.get("aggregate_version", 1),
                    version=event_data.get("version", 1),
                )
        return obj

    def to_snapshot(self) -> Dict[str, Any]:
        """Create a snapshot of the aggregate state."""
        state: Dict[str, Any] = {
            "id": str(self.id),
            "version": self.version,
            "counter": self.counter,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

        if self.last_event:
            state["last_event"] = {
                "event_type": self.last_event.__class__.__name__,
                "event_id": str(self.last_event.event_id),
                "aggregate_id": str(self.last_event.aggregate_id),
                "aggregate_version": getattr(self.last_event, "aggregate_version", 1),
                "occurred_on": self.last_event.occurred_on.isoformat(),
                "version": getattr(self.last_event, "version", 1),
            }

            # Add event-specific fields
            if isinstance(self.last_event, MockEvent):
                state["last_event"]["value"] = self.last_event.value
            elif isinstance(self.last_event, AnotherTestEvent):
                state["last_event"].update(
                    {"name": self.last_event.name, "amount": self.last_event.amount}
                )

        return state


class MockAggregateWithError(MockAggregate):
    """Test aggregate that raises an error during event handling."""

    def on_TestEvent(self, event: MockEvent) -> None:
        """Raise an error during event handling."""
        raise ValueError("Intentional error for testing")


# Fixtures
@pytest.fixture
def aggregate() -> MockAggregate:
    """Create a test aggregate with default values."""
    return MockAggregate()


# Tests
def test_aggregate_creation(aggregate: MockAggregate) -> None:
    """Test aggregate creation with default values."""
    assert isinstance(aggregate.id, UUID)
    assert aggregate.version == 0
    assert not aggregate.pending_events
    assert isinstance(aggregate.created_at, datetime)
    assert isinstance(aggregate.updated_at, datetime)
    assert aggregate.counter == 0
    assert aggregate.name == ""


def test_raise_and_handle_event(aggregate: MockAggregate) -> None:
    """Test raising and handling an event."""
    # Act
    aggregate.increment(5)

    # Assert
    assert aggregate.counter == 5
    assert len(aggregate.pending_events) == 1

    event = aggregate.pending_events[0]
    assert isinstance(event, MockEvent)
    assert event.value == 5
    assert event.aggregate_id == aggregate.id
    assert event.aggregate_version == 1


def test_multiple_events(aggregate: MockAggregate) -> None:
    """Test handling multiple events."""
    # Act
    aggregate.increment(3)
    aggregate.set_name("Test")
    aggregate.increment(2)

    # Assert
    assert aggregate.counter == 5
    assert aggregate.name == "Test"
    assert len(aggregate.pending_events) == 3

    # Check event order and versions
    events = aggregate.pending_events
    assert isinstance(events[0], MockEvent)
    assert events[0].aggregate_version == 1

    assert isinstance(events[1], AnotherTestEvent)
    assert events[1].aggregate_version == 2

    assert isinstance(events[2], MockEvent)
    assert events[2].aggregate_version == 3


def test_clear_events(aggregate: MockAggregate) -> None:
    """Test clearing pending events."""
    # Arrange
    aggregate.increment(1)
    assert aggregate.pending_events

    # Act
    aggregate.clear_events()

    # Assert
    assert not aggregate.pending_events


def test_from_events() -> None:
    """Test reconstructing an aggregate from events."""
    # Arrange
    aggregate_id = uuid4()
    events = [
        MockEvent(
            event_id=uuid4(),
            aggregate_id=aggregate_id,
            aggregate_version=1,
            value=10,
            occurred_on=datetime.now(timezone.utc),
            version=1,
        ),
        AnotherTestEvent(
            event_id=uuid4(),
            aggregate_id=aggregate_id,
            aggregate_version=2,
            name="Reconstructed",
            amount=11.0,
            occurred_on=datetime.now(timezone.utc),
            version=1,
        ),
    ]

    # Act
    reconstructed = MockAggregate.from_events(events)

    # Assert
    assert reconstructed.id == aggregate_id
    assert reconstructed.version == 2
    assert reconstructed.counter == 10
    assert reconstructed.name == "Reconstructed"
    assert not reconstructed.pending_events


def test_thread_safety() -> None:
    """Test that event application is thread-safe."""
    # Arrange
    aggregate = MockAggregate()
    num_threads = 10
    increments_per_thread = 100

    def increment_in_thread() -> None:
        for _ in range(increments_per_thread):
            aggregate.increment(1)

    # Act
    threads = []
    for _ in range(num_threads):
        t = threading.Thread(target=increment_in_thread)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Assert
    assert aggregate.counter == num_threads * increments_per_thread
    assert aggregate.version == num_threads * increments_per_thread
    assert len(aggregate.pending_events) == num_threads * increments_per_thread


def test_snapshot() -> None:
    """Test creating and restoring from a snapshot."""
    # Arrange
    aggregate = MockAggregate()
    aggregate.increment(5)
    aggregate.set_name("Snapshot Test")

    # Clear pending events to simulate persistence
    aggregate.clear_events()

    # Create a snapshot
    snapshot = aggregate.to_snapshot()

    # Act - Create a new aggregate from the snapshot
    restored = MockAggregate.from_snapshot(snapshot)

    # Assert
    assert restored.id == aggregate.id
    assert restored.version == aggregate.version
    assert restored.counter == 5
    assert restored.name == "Snapshot Test"
    assert restored.last_event is not None
    assert isinstance(restored.last_event, AnotherTestEvent)
    assert restored.last_event.name == "Snapshot Test"


def test_error_handling() -> None:
    """Test error handling during event application."""
    # Arrange
    aggregate = MockAggregateWithError()

    # Act/Assert
    with pytest.raises(
        ValueError,
        match="Error applying event MockEvent to MockAggregateWithError: Intentional error for testing",
    ):
        aggregate.increment(1)

    # The event should still be pending despite the error
    assert len(aggregate.pending_events) == 1


def test_event_metadata() -> None:
    """Test that event metadata is properly set."""
    # Arrange
    aggregate = MockAggregate()

    # Act
    aggregate.increment(10)

    # Assert
    event = aggregate.pending_events[0]
    assert event.aggregate_id == aggregate.id
    assert event.aggregate_version == 1
    assert event.occurred_on is not None
    assert event.version == 1  # Default version from DomainEvent


def test_concurrent_modification() -> None:
    """Test optimistic concurrency control."""
    # This test simulates a concurrent modification scenario
    # where two threads try to modify the aggregate simultaneously

    # Arrange
    aggregate = MockAggregate()

    # First thread increments the counter
    aggregate.increment(5)

    # Store the current version for assertion
    current_version = aggregate.version

    # Simulate loading the aggregate in another context (e.g., from event store)
    def modify_aggregate() -> None:
        # This would normally come from the event store
        fresh_aggregate = MockAggregate()
        fresh_aggregate.increment(3)  # This would be version 1 in this context

    # Act
    modify_aggregate()

    # Assert that the versions are tracked correctly
    assert aggregate.version == current_version
    assert len(aggregate.pending_events) == 1

    # The pending events should have the correct versions
    assert aggregate.pending_events[0].aggregate_version == current_version


def test_event_ordering() -> None:
    """Test that events are applied in the correct order."""
    # Arrange
    aggregate = MockAggregate()

    # Act
    aggregate.increment(1)
    aggregate.set_name("Test")
    aggregate.increment(2)

    # Assert
    events = aggregate.pending_events
    assert len(events) == 3
    assert isinstance(events[0], MockEvent)
    assert isinstance(events[1], AnotherTestEvent)
    assert isinstance(events[2], MockEvent)

    # Check that the versions are sequential
    assert events[0].aggregate_version == 1
    assert events[1].aggregate_version == 2
    assert events[2].aggregate_version == 3


def test_immutable_events() -> None:
    """Test that events are immutable after being applied."""
    # Arrange
    aggregate = MockAggregate()

    # Act
    aggregate.increment(5)
    event = aggregate.pending_events[0]
    assert isinstance(event, MockEvent)

    # Assert immutability by checking that we can't modify the event
    with pytest.raises(ValueError, match="MockEvent is immutable"):
        event.value = 10  # type: ignore[misc]  # This is expected to raise an error

    # But we can create a new event with the modified value
    new_event = MockEvent(
        value=10,
        aggregate_id=event.aggregate_id,
        aggregate_version=event.aggregate_version,
        occurred_on=event.occurred_on,
        version=event.version,
    )

    assert new_event.value == 10
