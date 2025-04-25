import asyncio
from typing import Any

import pytest

from uno.core.events.event_store import EventStore
from uno.core.events.events import DomainEvent
from uno.core.logging.logger import LoggerService, LoggingConfig


class DummyEvent(DomainEvent):
    event_type: str = "dummy"
    payload: dict[str, Any] = {}

@pytest.mark.asyncio
async def test_event_store_interface_abstract_methods():
    class DummyStore(EventStore[DummyEvent]):
        pass
    store = DummyStore()
    with pytest.raises(NotImplementedError):
        await store.get_events()

@pytest.mark.asyncio
async def test_in_memory_event_store_basic(monkeypatch):
    from uno.core.events.event_store import InMemoryEventStore

    logger = LoggerService(LoggingConfig())
    await logger.initialize()
    store = InMemoryEventStore(DummyEvent, logger)

    event = DummyEvent(aggregate_id="agg1", event_type="dummy", payload={"foo": "bar"})
    await store.save_event(event)
    events = await store.get_events(aggregate_id="agg1")
    assert len(events) == 1
    assert events[0].aggregate_id == "agg1"
    assert events[0].payload["foo"] == "bar"

@pytest.mark.asyncio
async def test_in_memory_event_store_multiple_aggregates():
    from uno.core.events.event_store import InMemoryEventStore

    logger = LoggerService(LoggingConfig())
    await logger.initialize()
    store = InMemoryEventStore(DummyEvent, logger)

    e1 = DummyEvent(aggregate_id="a1", event_type="dummy", payload={"x": 1})
    e2 = DummyEvent(aggregate_id="a2", event_type="dummy", payload={"x": 2})
    await store.save_event(e1)
    await store.save_event(e2)
    events_a1 = await store.get_events(aggregate_id="a1")
    events_a2 = await store.get_events(aggregate_id="a2")
    assert len(events_a1) == 1
    assert len(events_a2) == 1
    assert events_a1[0].payload["x"] == 1
    assert events_a2[0].payload["x"] == 2

@pytest.mark.asyncio
async def test_in_memory_event_store_event_type_filter():
    from uno.core.events.event_store import InMemoryEventStore

    logger = LoggerService(LoggingConfig())
    await logger.initialize()
    store = InMemoryEventStore(DummyEvent, logger)

    e1 = DummyEvent(aggregate_id="agg1", event_type="foo", payload={})
    e2 = DummyEvent(aggregate_id="agg1", event_type="bar", payload={})
    await store.save_event(e1)
    await store.save_event(e2)
    foo_events = await store.get_events(aggregate_id="agg1", event_type="foo")
    bar_events = await store.get_events(aggregate_id="agg1", event_type="bar")
    assert len(foo_events) == 1
    assert foo_events[0].event_type == "foo"
    assert len(bar_events) == 1
    assert bar_events[0].event_type == "bar"

@pytest.mark.asyncio
async def test_in_memory_event_store_limit():
    from uno.core.events.event_store import InMemoryEventStore

    logger = LoggerService(LoggingConfig())
    await logger.initialize()
    store = InMemoryEventStore(DummyEvent, logger)

    for i in range(5):
        e = DummyEvent(aggregate_id="agg1", event_type="dummy", payload={"i": i})
        await store.save_event(e)
    limited = await store.get_events(aggregate_id="agg1", limit=3)
    assert len(limited) == 3

@pytest.mark.asyncio
async def test_in_memory_event_store_missing_aggregate_id():
    from uno.core.events.event_store import InMemoryEventStore

    logger = LoggerService(LoggingConfig())
    await logger.initialize()
    store = InMemoryEventStore(DummyEvent, logger)

    event = DummyEvent(event_type="dummy", payload={})
    with pytest.raises(ValueError):
        await store.save_event(event)

@pytest.mark.asyncio
async def test_in_memory_event_store_no_events():
    from uno.core.events.event_store import InMemoryEventStore

    logger = LoggerService(LoggingConfig())
    await logger.initialize()
    store = InMemoryEventStore(DummyEvent, logger)

    events = await store.get_events(aggregate_id="doesnotexist")
    assert events == []

@pytest.mark.asyncio
async def test_in_memory_event_store_multiple_events_same_aggregate():
    from uno.core.events.event_store import InMemoryEventStore

    logger = LoggerService(LoggingConfig())
    await logger.initialize()
    store = InMemoryEventStore(DummyEvent, logger)

    e1 = DummyEvent(aggregate_id="agg1", event_type="dummy", payload={"n": 1})
    e2 = DummyEvent(aggregate_id="agg1", event_type="dummy", payload={"n": 2})
    await store.save_event(e1)
    await store.save_event(e2)
    events = await store.get_events(aggregate_id="agg1")
    assert len(events) == 2
    assert {ev.payload["n"] for ev in events} == {1, 2}

@pytest.mark.asyncio
async def test_in_memory_event_store_aggregate_and_type_filter():
    from uno.core.events.event_store import InMemoryEventStore

    logger = LoggerService(LoggingConfig())
    await logger.initialize()
    store = InMemoryEventStore(DummyEvent, logger)

    e1 = DummyEvent(aggregate_id="agg1", event_type="foo", payload={})
    e2 = DummyEvent(aggregate_id="agg1", event_type="bar", payload={})
    e3 = DummyEvent(aggregate_id="agg2", event_type="foo", payload={})
    await store.save_event(e1)
    await store.save_event(e2)
    await store.save_event(e3)
    filtered = await store.get_events(aggregate_id="agg1", event_type="foo")
    assert len(filtered) == 1
    assert filtered[0].aggregate_id == "agg1"
    assert filtered[0].event_type == "foo"

@pytest.mark.asyncio
async def test_in_memory_event_store_concurrent_writes_reads():
    from uno.core.events.event_store import InMemoryEventStore

    logger = LoggerService(LoggingConfig())
    await logger.initialize()
    store = InMemoryEventStore(DummyEvent, logger)

    async def writer(aggregate_id, n):
        for i in range(n):
            e = DummyEvent(aggregate_id=aggregate_id, event_type="concurrent", payload={"i": i})
            await store.save_event(e)

    async def reader(aggregate_id, n):
        # Wait a bit to let some events be written
        await asyncio.sleep(0.01)
        events = await store.get_events(aggregate_id=aggregate_id)
        # Should be between 0 and n events depending on timing
        assert all(ev.aggregate_id == aggregate_id for ev in events)

    tasks = []
    for agg in ["aggA", "aggB"]:
        tasks.append(writer(agg, 10))
        tasks.append(reader(agg, 10))
    await asyncio.gather(*tasks)
    # After all done, all events should be present
    for agg in ["aggA", "aggB"]:
        events = await store.get_events(aggregate_id=agg)
        assert len(events) == 10

@pytest.mark.asyncio
async def test_in_memory_event_store_large_and_unicode_payloads():
    from uno.core.events.event_store import InMemoryEventStore

    logger = LoggerService(LoggingConfig())
    await logger.initialize()
    store = InMemoryEventStore(DummyEvent, logger)

    large_payload = {"data": "x" * 100_000}
    unicode_payload = {"emoji": "😀🐍✨", "text": "こんにちは世界"}
    e1 = DummyEvent(aggregate_id="agg1", event_type="large", payload=large_payload)
    e2 = DummyEvent(aggregate_id="agg1", event_type="unicode", payload=unicode_payload)
    await store.save_event(e1)
    await store.save_event(e2)
    events = await store.get_events(aggregate_id="agg1")
    assert any("x" * 100_000 in str(ev.payload.get("data", "")) for ev in events)
    assert any("emoji" in ev.payload and "世界" in ev.payload.get("text", "") for ev in events)

@pytest.mark.asyncio
async def test_in_memory_event_store_order_preservation():
    from uno.core.events.event_store import InMemoryEventStore

    logger = LoggerService(LoggingConfig())
    await logger.initialize()
    store = InMemoryEventStore(DummyEvent, logger)

    events_in = [DummyEvent(aggregate_id="agg1", event_type="order", payload={"n": i}) for i in range(10)]
    for ev in events_in:
        await store.save_event(ev)
    events_out = await store.get_events(aggregate_id="agg1")
    assert [ev.payload["n"] for ev in events_out] == list(range(10))

@pytest.mark.asyncio
async def test_in_memory_event_store_immutability():
    from uno.core.events.event_store import InMemoryEventStore

    logger = LoggerService(LoggingConfig())
    await logger.initialize()
    store = InMemoryEventStore(DummyEvent, logger)

    e1 = DummyEvent(aggregate_id="agg1", event_type="immut", payload={"foo": "bar"})
    await store.save_event(e1)
    events = await store.get_events(aggregate_id="agg1")
    events[0].payload["foo"] = "changed"
    # Fetch again, should not be changed if store is isolated
    events2 = await store.get_events(aggregate_id="agg1")
    # If the store returns references, this will fail
    assert events2[0].payload["foo"] == "bar"

@pytest.mark.asyncio
async def test_in_memory_event_store_invalid_event_type():
    from uno.core.events.event_store import InMemoryEventStore

    logger = LoggerService(LoggingConfig())
    await logger.initialize()
    store = InMemoryEventStore(DummyEvent, logger)

    class NotADomainEvent:
        pass
    not_event = NotADomainEvent()
    with pytest.raises(ValueError):
        await store.save_event(not_event)  # Should fail due to missing aggregate_id

# Note: For PostgresEventStore, integration tests should be added with a test database and asyncpg/SQLAlchemy mocks or fixtures.
# These are omitted here for brevity, but the interface is ready for extension.
