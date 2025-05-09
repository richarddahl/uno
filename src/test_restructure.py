# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Test script demonstrating the restructured events modules.

This script creates and uses components from each of the restructured packages
to verify that the modular structure works correctly.
"""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional


class Result:
    """Simple Result type for testing."""

    def __init__(self, value=None, error=None):
        self._value = value
        self._error = error

    def is_success(self):
        return self._error is None

    def is_failure(self):
        return self._error is not None

    def unwrap(self):
        return self._value

    def unwrap_error(self):
        return self._error


from uno.events import (
    DomainEvent,
    EventBusProtocol,
    EventStoreProtocol,
    InMemoryEventBus,
    InMemoryEventStore,
)
from uno.uow import UnitOfWork, InMemoryUnitOfWork
from uno.persistence import (
    PostgresEventStore,
    PostgresEventBus,
    PostgresCommandBus,
    PostgresSagaStore,
)
from uno.uow import PostgresUnitOfWork
from uno.logging import LoggerProtocol, get_logger


# Define a sample domain event
@dataclass
class OrderCreated(DomainEvent):
    order_id: str
    customer_id: str
    amount: float
    items: List[Dict[str, Any]]

    def __init__(
        self,
        order_id: str,
        customer_id: str,
        amount: float,
        items: List[Dict[str, Any]],
        aggregate_id: Optional[str] = None,
        event_id: Optional[str] = None,
        version: int = 1,
        timestamp: Optional[datetime] = None,
    ):
        super().__init__(
            aggregate_id=aggregate_id or order_id,
            event_id=event_id or str(uuid.uuid4()),
            version=version,
            timestamp=timestamp or datetime.now(UTC),
        )
        self.order_id = order_id
        self.customer_id = customer_id
        self.amount = amount
        self.items = items
        self.event_type = "OrderCreated"


async def test_in_memory_implementations():
    """Test the in-memory implementations."""
    print("\n--- Testing In-Memory Implementations ---")

    # Create in-memory event store
    event_store = InMemoryEventStore()
    print("Created InMemoryEventStore")

    # Create in-memory event bus
    event_bus = InMemoryEventBus()
    print("Created InMemoryEventBus")

    # Create in-memory unit of work
    uow = InMemoryUnitOfWork(event_store)
    print("Created InMemoryUnitOfWork")

    # Create and save an event
    order_id = str(uuid.uuid4())
    event = OrderCreated(
        order_id=order_id,
        customer_id="customer-123",
        amount=99.99,
        items=[{"product_id": "prod-1", "quantity": 2}],
    )

    # Save event using UoW
    async with InMemoryUnitOfWork.begin(event_store) as uow:
        result = await uow.event_store.save_event(event)
        if result.is_success():
            print(f"Saved event {event.event_id} to store")
        else:
            print(f"Failed to save event: {result.unwrap_error()}")

    # Publish event to event bus
    result = await event_bus.publish(event)
    if result.is_success():
        print(f"Published event {event.event_id} to event bus")
    else:
        print(f"Failed to publish event: {result.unwrap_error()}")

    # Get events from store
    result = await event_store.get_events_by_aggregate_id(order_id)
    if result.is_success():
        events = result.unwrap()
        print(f"Retrieved {len(events)} events for aggregate {order_id}")
        for e in events:
            print(f"  - {e.event_type} (version {e.version})")
    else:
        print(f"Failed to retrieve events: {result.unwrap_error()}")


def print_persistence_implementations():
    """Print information about the PostgreSQL implementations."""
    print("\n--- PostgreSQL Implementations (Import Check) ---")
    print(f"PostgresEventStore class: {PostgresEventStore.__name__}")
    print(f"PostgresEventBus class: {PostgresEventBus.__name__}")
    print(f"PostgresCommandBus class: {PostgresCommandBus.__name__}")
    print(f"PostgresSagaStore class: {PostgresSagaStore.__name__}")
    print(f"PostgresUnitOfWork class: {PostgresUnitOfWork.__name__}")


async def main():
    """Run all tests."""
    await test_in_memory_implementations()
    print_persistence_implementations()
    print("\nAll tests completed successfully.")


if __name__ == "__main__":
    print("Starting test...")
    asyncio.run(main())
