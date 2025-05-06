"""
Integration tests for PostgresEventStore in Uno.
Covers: CRUD, replay, concurrency/version conflict, upcasting, and error scenarios.
"""

import asyncio

# --- Fixtures ---
import os
import pytest
from datetime import UTC, datetime
from typing import ClassVar, AsyncGenerator
from uuid import uuid4
from datetime import UTC, datetime

from uno.core.events.base_event import DomainEvent
from uno.core.events.postgres_event_store import PostgresEventStore
from uno.infrastructure.di.providers.database import (
    db_engine_factory,
    db_session_factory,
    register_database_services,
)
from uno.infrastructure.logging.logger import LoggerService, LoggingConfig


# --- Fast, isolated unit test fixture using in-memory SQLite ---
@pytest.fixture(scope="function")
async def override_db_provider() -> AsyncGenerator[None, None]:
    # Create a new service collection
    services = ServiceCollection()
    
    # Register database services with test configuration
    register_database_services(services, {
        "backend": "postgres",
        "dsn": "postgresql+asyncpg://postgres:postgres@localhost:5432/uno_test",
        "pool_size": 5
    })
    
    # Create the database engine and session
    engine = db_engine_factory()
    async with db_session_factory(engine) as session:
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Set up the test database
        async with session.begin():
            await session.execute(text("CREATE SCHEMA IF NOT EXISTS uno"))
            await session.execute(text("CREATE SCHEMA IF NOT EXISTS uno_events"))
            await session.execute(text("CREATE SCHEMA IF NOT EXISTS uno_audit"))
        
        # Yield control to the test
        yield
        
        # Clean up
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            
        await engine.dispose()


@pytest.fixture(scope="function")
async def pg_event_store(override_db_provider: None) -> PostgresEventStore:
    # Use the overridden in-memory engine/session for fast tests
    engine = db_engine_factory()
    async with db_session_factory(engine) as session:
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


# --- Integration test fixture using real Postgres backend ---
@pytest.fixture(scope="function")
async def pg_event_store_postgres(override_db_provider: None) -> PostgresEventStore:
    # Uses the default configured Postgres backend (do not override provider)
    engine = db_engine_factory()
    async with db_session_factory(engine) as session:
        store = PostgresEventStore(db_session=session)
    provider = get_service_provider()
    engine = provider.get_service(AsyncSession)
    session = provider.get_service(AsyncSession)
    store = PostgresEventStore(db_session=session)
    session = provider.get_service(AsyncSession)
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
    event_type: ClassVar[str] = "fake_event"
    aggregate_id: str
    version: int
    timestamp: datetime = datetime.now(UTC)
    foo: str

    def __init__(self, aggregate_id: str, version: int, foo: str) -> None:
        self.aggregate_id = aggregate_id
        self.version = version
        self.foo = foo
        self.timestamp = datetime.now(UTC)


# --- Tests ---
@pytest.mark.asyncio
async def test_save_and_get_event(pg_event_store: PostgresEventStore) -> None:
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
async def test_replay_multiple_events(pg_event_store: PostgresEventStore) -> None:
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
async def test_concurrency_conflict(pg_event_store: PostgresEventStore) -> None:
    agg_id = str(uuid4())
    event1 = FakeEvent(aggregate_id=agg_id, version=1, foo="x")
    event2 = FakeEvent(aggregate_id=agg_id, version=1, foo="y")
    res1 = await pg_event_store.save_event(event1)
    assert isinstance(res1, Success)
    res2 = await pg_event_store.save_event(event2)
    assert isinstance(res2, Failure)  # Should fail on version conflict


@pytest.mark.asyncio
async def test_event_type_filter(pg_event_store: PostgresEventStore) -> None:
    agg_id = str(uuid4())
    event_a = FakeEvent(aggregate_id=agg_id, version=1, foo="a")
    await pg_event_store.save_event(event_a)
    fetched = await pg_event_store.get_events(event_type="fake_event")
    assert isinstance(fetched, Success)
    assert any(e.foo == "a" for e in fetched.unwrap())


@pytest.mark.asyncio
async def test_error_handling(pg_event_store: PostgresEventStore) -> None:
    # Simulate error: missing required field
    event = FakeEvent(aggregate_id=None, version=1, foo="bad")  # type: ignore
    res = await pg_event_store.save_event(event)
    assert isinstance(res, Failure)
    # Simulate error: DB down
    provider = get_service_provider()
    session = provider.get_service(AsyncSession)
    bad_store = PostgresEventStore(db_session=session)
    event = FakeEvent(aggregate_id=str(uuid4()), version=1, foo="fail")
    res = await bad_store.save_event(event)
    assert isinstance(res, Failure)
