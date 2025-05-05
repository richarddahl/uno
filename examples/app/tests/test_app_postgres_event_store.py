"""
Integration tests for PostgresEventStore using real Uno domain events.
Covers: CRUD, replay, upcasting, error scenarios, and compatibility with example app events.
"""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest

# Import real domain events from the example app
from examples.app.domain.inventory.events import MassMeasured, VolumeMeasured
from examples.app.domain.inventory.value_objects import Mass, Volume
from examples.app.domain.vendor.value_objects import EmailAddress
from uno.core.errors.result import Failure, Success
from uno.core.events.postgres_event_store import PostgresEventStore
from uno.infrastructure.di import (
    ServiceCollection,
    get_service_provider,
    initialize_services,
    shutdown_services,
)
from uno.infrastructure.di.provider import reset_global_service_provider
from uno.infrastructure.di.providers.database import (
    get_db_engine,
    get_db_session,
    register_database_services,
)
from uno.infrastructure.logging.logger import LoggerService, LoggingConfig


@pytest.fixture(scope="function")
async def override_db_provider() -> None:
    reset_global_service_provider()
    import os

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
    engine = get_service_provider().get_service("db_engine")
    session = get_service_provider().get_service("db_session")
    store = PostgresEventStore(db_session=session)
    async with engine.begin() as conn:
        await conn.run_sync(store.metadata.create_all)
    try:
        yield store
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(store.metadata.drop_all)
        reset_global_service_provider()


@pytest.mark.asyncio
async def test_save_and_get_mass_measured(pg_event_store):
    event = MassMeasured.create(
        aggregate_id="item-1",
        mass=Mass(value=10.0, unit="kg"),
        measured_by=EmailAddress(value="user@example.com"),
    ).unwrap()
    result = await pg_event_store.save_event(event)
    assert isinstance(result, Success)

    fetched = await pg_event_store.get_events(aggregate_id="item-1")
    assert isinstance(fetched, Success)
    events = fetched.unwrap()
    assert len(events) == 1
    assert isinstance(events[0], MassMeasured)
    assert events[0].mass.value == 10.0
    assert events[0].mass.unit == "kg"


@pytest.mark.asyncio
async def test_save_and_get_volume_measured(pg_event_store):
    event = VolumeMeasured.create(
        vessel_id="vessel-1",
        volume=Volume(value=100.0, unit="L"),
        measured_by=EmailAddress(value="admin@example.com"),
    ).unwrap()
    # For this event, we treat vessel_id as aggregate_id in the store
    event_dict = event.model_dump()
    event_dict["aggregate_id"] = event.vessel_id
    event = VolumeMeasured(**event_dict)
    result = await pg_event_store.save_event(event)
    assert isinstance(result, Success)

    fetched = await pg_event_store.get_events(aggregate_id="vessel-1")
    assert isinstance(fetched, Success)
    events = fetched.unwrap()
    assert len(events) == 1
    assert isinstance(events[0], VolumeMeasured)
    assert events[0].volume.value == 100.0
    assert events[0].volume.unit == "L"


@pytest.mark.asyncio
async def test_upcast_and_error_paths(pg_event_store):
    # Simulate an old-version event (no upcast implemented)
    event = MassMeasured.create(
        aggregate_id="item-2",
        mass=Mass(value=5.0, unit="kg"),
        measured_by=EmailAddress(value="test@example.com"),
    ).unwrap()
    # Manually set a bogus version for upcast failure
    event_dict = event.model_dump()
    event_dict["version"] = 99
    event = MassMeasured(**event_dict)
    result = await pg_event_store.save_event(event)
    assert isinstance(result, Success)
    fetched = await pg_event_store.get_events(aggregate_id="item-2")
    assert isinstance(fetched, Success)
    events = fetched.unwrap()
    # Should fail upcast and return Failure for each event
    for e in events:
        upcast_result = e.upcast(target_version=1)
        assert isinstance(upcast_result, Failure)


@pytest.mark.asyncio
async def test_empty_event_stream(pg_event_store):
    fetched = await pg_event_store.get_events(aggregate_id="does-not-exist")
    assert isinstance(fetched, Success)
    assert fetched.unwrap() == []
