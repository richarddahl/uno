"""
Unit tests for InMemoryEventStore with strict DI-LoggerService injection.
"""

import pytest
from unittest.mock import MagicMock
import unittest.mock
from uno.core.events.base_event import DomainEvent
from uno.core.events.event_store import InMemoryEventStore
from uno.infrastructure.logging.logger import LoggerService
from uno.core.errors.result import Success, Failure


class FakeEvent(DomainEvent):
    event_type: str = "fake_event"
    aggregate_id: str
    version: int
    foo: str


def make_logger():
    logger = MagicMock(spec=LoggerService)
    logger.structured_log = MagicMock()
    return logger


@pytest.mark.asyncio
async def test_save_event_success():
    logger = make_logger()
    store = InMemoryEventStore(logger)
    event = FakeEvent(aggregate_id="agg-1", version=1, foo="bar")
    res = await store.save_event(event)
    assert isinstance(res, Success)
    logger.structured_log.assert_any_call(
        "INFO",
        f"Saved event {event.event_type} for aggregate {event.aggregate_id}",
        name="uno.events.inmem",
    )


@pytest.mark.asyncio
async def test_save_event_failure():
    logger = make_logger()
    store = InMemoryEventStore(logger)
    # Simulate failure by monkeypatching _events to None
    store._events = None  # type: ignore
    event = FakeEvent(aggregate_id="agg-1", version=1, foo="fail")
    res = await store.save_event(event)
    assert isinstance(res, Failure)
    logger.structured_log.assert_any_call(
        "ERROR", unittest.mock.ANY, name="uno.events.inmem", error=res.error
    )


@pytest.mark.asyncio
async def test_get_events_filters_and_logs():
    logger = make_logger()
    store = InMemoryEventStore(logger)
    e1 = FakeEvent(aggregate_id="agg-1", version=1, foo="a")
    e2 = FakeEvent(aggregate_id="agg-2", version=1, foo="b")
    await store.save_event(e1)
    await store.save_event(e2)
    res = await store.get_events(aggregate_id="agg-1")
    assert isinstance(res, Success)
    events = res.unwrap()
    assert len(events) == 1 and events[0].aggregate_id == "agg-1"
    logger.structured_log.assert_any_call(
        "INFO", "Retrieved 1 events from store", name="uno.events.inmem"
    )


@pytest.mark.asyncio
async def test_get_events_by_aggregate_id_success():
    logger = make_logger()
    store = InMemoryEventStore(logger)
    e1 = FakeEvent(aggregate_id="agg-1", version=1, foo="a")
    await store.save_event(e1)
    res = await store.get_events_by_aggregate_id("agg-1")
    assert isinstance(res, Success)
    events = res.unwrap()
    assert len(events) == 1 and events[0].aggregate_id == "agg-1"


@pytest.mark.asyncio
async def test_get_events_by_aggregate_id_failure():
    logger = make_logger()
    store = InMemoryEventStore(logger)
    # No events for this aggregate
    res = await store.get_events_by_aggregate_id("missing")
    assert isinstance(res, Success)
    assert res.unwrap() == []

    # Simulate error by monkeypatching _events
    store._events = None  # type: ignore
    res = await store.get_events_by_aggregate_id("agg-1")
    assert isinstance(res, Failure)
    logger.structured_log.assert_any_call(
        "ERROR", unittest.mock.ANY, name="uno.events.inmem", error=res.error
    )
