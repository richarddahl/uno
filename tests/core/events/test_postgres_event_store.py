import asyncio

import pytest

# Workaround for event loop policy issue on Python 3.13+
asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from uno.core.config.database import database_config
from uno.core.events.postgres_event_store import PostgresEventStore
from uno.core.events.events import DomainEvent
from uno.core.logging.logger import LoggerService, LoggingConfig

# --- Fixtures ---

@pytest.fixture(scope="function")
async def postgres_test_db():
    # Use test DB config (ensure this is isolated and safe for CI/dev)
    db_url = database_config.TEST_DB_URL  # e.g. "postgresql+asyncpg://user:pw@localhost:5432/uno_test"
    engine = create_async_engine(db_url, echo=True)
    async with engine.begin() as conn:
        # Drop and recreate the domain_events table for a clean slate
        await conn.execute(text("DROP TABLE IF EXISTS domain_events CASCADE"))
        await conn.execute(text("""
        CREATE TABLE domain_events (
            event_id VARCHAR PRIMARY KEY,
            event_type VARCHAR NOT NULL,
            aggregate_id VARCHAR NOT NULL,
            aggregate_type VARCHAR NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            data JSONB NOT NULL,
            metadata JSONB
        )
        """))
    yield db_url
    await engine.dispose()

@pytest.fixture(scope="function")
async def postgres_event_store(postgres_test_db):
    logger = LoggerService(LoggingConfig())
    await logger.initialize()
    store = PostgresEventStore(DomainEvent, logger)
    return store

# --- Test Scenarios ---
@pytest.mark.asyncio
async def test_save_and_get_event(postgres_event_store):
    event = DomainEvent(
        event_id="e1",
        event_type="created",
        aggregate_id="agg1",
        aggregate_type="TestAggregate"
    )
    await postgres_event_store.save_event(event)
    events = await postgres_event_store.get_events(aggregate_id="agg1")
    assert len(events) == 1
    assert events[0].event_id == "e1"

@pytest.mark.asyncio
async def test_multiple_aggregates(postgres_event_store):
    e1 = DomainEvent(event_id="e2", event_type="foo", aggregate_id="aggA", aggregate_type="Agg")
    e2 = DomainEvent(event_id="e3", event_type="bar", aggregate_id="aggB", aggregate_type="Agg")
    await postgres_event_store.save_event(e1)
    await postgres_event_store.save_event(e2)
    a_events = await postgres_event_store.get_events(aggregate_id="aggA")
    b_events = await postgres_event_store.get_events(aggregate_id="aggB")
    assert len(a_events) == 1
    assert len(b_events) == 1
    assert a_events[0].event_type == "foo"
    assert b_events[0].event_type == "bar"

@pytest.mark.asyncio
async def test_event_type_filter(postgres_event_store):
    e1 = DomainEvent(event_id="e4", event_type="typeA", aggregate_id="agg1", aggregate_type="Agg")
    e2 = DomainEvent(event_id="e5", event_type="typeB", aggregate_id="agg1", aggregate_type="Agg")
    await postgres_event_store.save_event(e1)
    await postgres_event_store.save_event(e2)
    type_a = await postgres_event_store.get_events(aggregate_id="agg1", event_type="typeA")
    type_b = await postgres_event_store.get_events(aggregate_id="agg1", event_type="typeB")
    assert len(type_a) == 1
    assert type_a[0].event_type == "typeA"
    assert len(type_b) == 1
    assert type_b[0].event_type == "typeB"

@pytest.mark.asyncio
async def test_limit(postgres_event_store):
    for i in range(5):
        e = DomainEvent(event_id=f"e{i+10}", event_type="lim", aggregate_id="agg2", aggregate_type="Agg")
        await postgres_event_store.save_event(e)
    limited = await postgres_event_store.get_events(aggregate_id="agg2", limit=3)
    assert len(limited) == 3

@pytest.mark.asyncio
async def test_order_preservation(postgres_event_store):
    events_in = [DomainEvent(event_id=f"order{i}", event_type="order", aggregate_id="agg3", aggregate_type="Agg") for i in range(10)]
    for ev in events_in:
        await postgres_event_store.save_event(ev)
    events_out = await postgres_event_store.get_events(aggregate_id="agg3")
    assert [ev.event_id for ev in events_out] == [f"order{i}" for i in range(10)]

@pytest.mark.asyncio
async def test_large_and_unicode_payloads(postgres_event_store):
    large_payload = {"data": "x" * 100_000}
    unicode_payload = {"emoji": "😀🐍✨", "text": "こんにちは世界"}
    e1 = DomainEvent(event_id="large1", event_type="large", aggregate_id="agg4", aggregate_type="Agg", payload=large_payload)
    e2 = DomainEvent(event_id="uni1", event_type="unicode", aggregate_id="agg4", aggregate_type="Agg", payload=unicode_payload)
    await postgres_event_store.save_event(e1)
    await postgres_event_store.save_event(e2)
    events = await postgres_event_store.get_events(aggregate_id="agg4")
    assert any("x" * 100_000 in str(ev.payload.get("data", "")) for ev in events)
    assert any("emoji" in ev.payload and "世界" in ev.payload.get("text", "") for ev in events)

@pytest.mark.asyncio
async def test_missing_aggregate_id(postgres_event_store):
    event = DomainEvent(event_id="noagg", event_type="fail", aggregate_type="Agg")
    with pytest.raises(Exception):
        await postgres_event_store.save_event(event)

@pytest.mark.asyncio
async def test_concurrent_writes_reads(postgres_event_store):
    async def writer(aggregate_id, n):
        for i in range(n):
            e = DomainEvent(event_id=f"c{aggregate_id}{i}", event_type="concurrent", aggregate_id=aggregate_id, aggregate_type="Agg")
            await postgres_event_store.save_event(e)
    async def reader(aggregate_id, n):
        await asyncio.sleep(0.01)
        events = await postgres_event_store.get_events(aggregate_id=aggregate_id)
        assert all(ev.aggregate_id == aggregate_id for ev in events)
    tasks = []
    for agg in ["aggA", "aggB"]:
        tasks.append(writer(agg, 10))
        tasks.append(reader(agg, 10))
    await asyncio.gather(*tasks)
    for agg in ["aggA", "aggB"]:
        events = await postgres_event_store.get_events(aggregate_id=agg)
        assert len(events) == 10
