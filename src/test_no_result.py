"""
Simple test script to verify the restructured Uno framework.

This script tests the core components after removing the Result monad pattern.
"""

import asyncio
import sys
from typing import Any

# Add the src directory to the path
sys.path.append("/Users/richarddahl/Code/uno/src")

from uno.events.base_event import DomainEvent
from uno.events.config import EventsConfig
from uno.events.implementations.bus import InMemoryEventBus
from uno.events.implementations.store import InMemoryEventStore
from uno.logging import LoggerProtocol, get_logger


# Create a simple test event
class TestEvent(DomainEvent):
    def __init__(self, aggregate_id: str, data: Any = None):
        super().__init__()
        self.aggregate_id = aggregate_id
        self.event_type = "TestEvent"
        self.version = 1
        self.data = data

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "aggregate_id": self.aggregate_id,
            "event_type": self.event_type,
            "version": self.version,
            "data": self.data,
        }


async def test_in_memory_components() -> None:
    """Test the in-memory components of the events package."""

    print("Testing in-memory components...")

    # Create logger
    logger: LoggerProtocol = get_logger("test_no_result")

    # Create event store
    event_store = InMemoryEventStore(logger)

    # Create event bus
    event_bus = InMemoryEventBus(logger, EventsConfig())

    # Create test event
    test_event = TestEvent(aggregate_id="test-123", data={"test": "value"})

    # Test event handler
    received_events = []

    async def event_handler(event: DomainEvent) -> None:
        print(f"Event received: {event.event_type} - {event.aggregate_id}")
        received_events.append(event)

    # Subscribe to event
    event_bus.subscribe("TestEvent", event_handler)

    # Save an event to the store
    print("Saving event to store...")
    await event_store.save_event(test_event)

    # Get events from store
    print("Getting events from store...")
    events = await event_store.get_events(aggregate_id="test-123")
    print(f"Retrieved {len(events)} events")

    # Publish event
    print("Publishing event...")
    await event_bus.publish(test_event)

    # Wait for event to be processed
    await asyncio.sleep(0.1)

    # Check if event was received
    assert len(received_events) == 1, f"Expected 1 event, got {len(received_events)}"
    assert received_events[0].aggregate_id == "test-123", "Event ID mismatch"

    print("All tests passed!")


async def main():
    await test_in_memory_components()


if __name__ == "__main__":
    asyncio.run(main())
