# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Integration tests for InMemoryEventStore using InventoryItem aggregate and events.
Covers event append, replay, error propagation, and type safety.
"""

import pytest
from uno.core.events.event_store import InMemoryEventStore
from uno.infrastructure.logging import LoggerService, LoggingConfig
from uno.core.errors.result import Success, Failure
from examples.app.domain.inventory import (
    InventoryItem,
    InventoryItemCreated,
    InventoryItemRenamed,
    InventoryItemAdjusted,
)


@pytest.fixture
def logger():
    return LoggerService(LoggingConfig())


@pytest.fixture
def event_store(logger):
    return InMemoryEventStore(logger)


@pytest.fixture
def item_created_event():
    result = InventoryItemCreated.create(
        aggregate_id="sku-1", name="Widget", quantity=100
    )
    assert isinstance(result, Success)
    return result.value


@pytest.fixture
def item_renamed_event():
    result = InventoryItemRenamed.create(aggregate_id="sku-1", new_name="Gizmo")
    assert isinstance(result, Success)
    return result.value


@pytest.fixture
def item_adjusted_event():
    result = InventoryItemAdjusted.create(aggregate_id="sku-1", adjustment=5)
    assert isinstance(result, Success)
    return result.value


import pytest


@pytest.mark.asyncio
async def test_save_and_replay_events(
    event_store, item_created_event, item_renamed_event, item_adjusted_event
):
    # Save events
    for event in [item_created_event, item_renamed_event, item_adjusted_event]:
        result = await event_store.save_event(event)
        assert isinstance(result, Success)

    # Replay events
    replay_result = await event_store.get_events_by_aggregate_id("sku-1")
    assert isinstance(replay_result, Success)
    events = replay_result.value
    assert len(events) == 3
    assert isinstance(events[0], InventoryItemCreated)
    assert isinstance(events[1], InventoryItemRenamed)
    assert isinstance(events[2], InventoryItemAdjusted)

    # Hydrate aggregate from events
    item = None
    for event in events:
        if isinstance(event, InventoryItemCreated):
            item = InventoryItem(
                id=event.aggregate_id, name=event.name, quantity=event.quantity
            )
        elif isinstance(event, InventoryItemRenamed) and item:
            item.name = event.new_name
        elif isinstance(event, InventoryItemAdjusted) and item:
            item.quantity = type(item.quantity).from_count(
                item.quantity.value.value + event.adjustment
            )
    assert item is not None
    assert item.id == "sku-1"
    assert item.name == "Gizmo"
    assert item.quantity.value.value == 105


import pytest


@pytest.mark.asyncio
async def test_event_store_error_propagation(event_store):
    # Try to save an event without aggregate_id
    class BadEvent:
        event_type = "BadEvent"

    bad_event = BadEvent()
    result = await event_store.save_event(bad_event)
    assert isinstance(result, Failure)
    assert isinstance(result.error, Exception)

    # Try to get events for missing aggregate
    replay_result = await event_store.get_events_by_aggregate_id("does-not-exist")
    assert isinstance(replay_result, Success)
    assert replay_result.value == []

    # Try to get events with filter
    # Save a valid event first
    item_event = InventoryItemCreated.create(
        aggregate_id="sku-2", name="Widget", quantity=10
    ).value
    await event_store.save_event(item_event)
    filtered_result = await event_store.get_events(
        aggregate_id="sku-2", event_type="InventoryItemCreated"
    )
    assert isinstance(filtered_result, Success)
    assert len(filtered_result.value) == 1
    assert isinstance(filtered_result.value[0], InventoryItemCreated)
