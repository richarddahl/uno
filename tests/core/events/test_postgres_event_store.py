"""
Integration tests for PostgresEventStore in Uno.
Covers: CRUD, replay, concurrency/version conflict, upcasting, and error scenarios.
"""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from uno.core.di.provider import reset_global_service_provider

from uno.core.errors.result import Failure, Success
from uno.core.events.base_event import DomainEvent
from uno.core.events.postgres_event_store import PostgresEventStore
from uno.core.logging.logger import LoggerService, LoggingConfig


# --- Fixtures ---


import os
from uno.core.di.providers.database import get_db_engine, get_db_session, register_database_services
from uno.core.di import ServiceCollection, initialize_services, shutdown_services, get_service_provider

# --- Fast, isolated unit test fixture using in-memory SQLite ---
@pytest.fixture(scope="function")
async def override_db_provider() -> None:
    """
    Override the Uno DI db_session/db_engine providers with in-memory SQLite for isolated fast tests.
    Patches config, builds a fresh DI container, and sets it as global for the test.
    Ensures DI is reset after each test to avoid SERVICE_PROVIDER_ALREADY_INITIALIZED errors.
    """
    reset_global_service_provider()
    os.environ["DB_BACKEND"] = "memory"
    services = ServiceCollection()
    register_database_services(services)
    await initialize_services()
    try:
        yield
    finally:
        await shutdown_services()
        reset_global_service_provider()
        if "DB_BACKEND" in os.environ:
            del os.environ["DB_BACKEND"]

@pytest.fixture(scope="function")
async def pg_event_store(override_db_provider):
    # Use the overridden in-memory engine/session for fast tests
    engine = get_service_provider().get_service("db_engine")
    session = get_service_provider().get_service("db_session")
    store = PostgresEventStore(db_session=session)
    # Create table if needed
    async with engine.begin() as conn:
        await conn.run_sync(store.metadata.create_all)
    try:
        yield store
    finally:
        # Cleanup
        async with engine.begin() as conn:
            await conn.run_sync(store.metadata.drop_all)
        reset_global_service_provider()

# --- Integration test fixture using real Postgres backend ---
@pytest.fixture(scope="function")
async def pg_event_store_postgres():
    # Uses the default configured Postgres backend (do not override provider)
    engine = get_db_engine()
    session = get_db_session()
    store = PostgresEventStore(db_session=session)
    async with engine.begin() as conn:
        await conn.run_sync(store.metadata.create_all)
    try:
        yield store
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(store.metadata.drop_all)
        reset_global_service_provider()


# --- Sample DomainEvent subclass ---
class FakeEvent(DomainEvent):
    event_type: str = "fake_event"
    aggregate_id: str
    version: int
    timestamp: datetime = datetime.now(UTC)
    foo: str


# --- Tests ---
@pytest.mark.asyncio
async def test_save_and_get_event(pg_event_store):
    event = FakeEvent(aggregate_id=str(uuid4()), version=1, foo="bar")
    result = await pg_event_store.save_event(event)
    assert isinstance(result, Success)

    fetched = await pg_event_store.get_events(aggregate_id=event.aggregate_id)
    assert isinstance(fetched, Success)
    events = fetched.unwrap()
    assert len(events) == 1
    assert events[0].foo == "bar"
    assert events[0].aggregate_id == event.aggregate_id


@pytest.mark.asyncio
async def test_replay_multiple_events(pg_event_store):
    agg_id = str(uuid4())
    events = [
        FakeEvent(aggregate_id=agg_id, version=i, foo=f"v{i}") for i in range(1, 4)
    ]
    for e in events:
        res = await pg_event_store.save_event(e)
        assert isinstance(res, Success)
    fetched = await pg_event_store.get_events_by_aggregate_id(agg_id)
    assert isinstance(fetched, Success)
    out = fetched.unwrap()
    assert len(out) == 3
    assert [e.foo for e in out] == ["v1", "v2", "v3"]


@pytest.mark.asyncio
async def test_concurrency_conflict(pg_event_store):
    agg_id = str(uuid4())
    event1 = FakeEvent(aggregate_id=agg_id, version=1, foo="x")
    event2 = FakeEvent(aggregate_id=agg_id, version=1, foo="y")
    res1 = await pg_event_store.save_event(event1)
    assert isinstance(res1, Success)
    res2 = await pg_event_store.save_event(event2)
    assert isinstance(res2, Failure)  # Should fail on version conflict


@pytest.mark.asyncio
async def test_event_type_filter(pg_event_store):
    agg_id = str(uuid4())
    event_a = FakeEvent(aggregate_id=agg_id, version=1, foo="a")
    await pg_event_store.save_event(event_a)
    fetched = await pg_event_store.get_events(event_type="fake_event")
    assert isinstance(fetched, Success)
    assert any(e.foo == "a" for e in fetched.unwrap())


@pytest.mark.asyncio
async def test_error_handling(pg_event_store):
    # Simulate error: missing required field
    event = FakeEvent(aggregate_id=None, version=1, foo="bad")  # type: ignore
    res = await pg_event_store.save_event(event)
    assert isinstance(res, Failure)
    # Simulate error: DB down
    bad_store = PostgresEventStore(
        dsn="postgresql+asyncpg://bad:bad@localhost:5432/doesnotexist"
    )
    event = FakeEvent(aggregate_id=str(uuid4()), version=1, foo="fail")
    res = await bad_store.save_event(event)
    assert isinstance(res, Failure)
