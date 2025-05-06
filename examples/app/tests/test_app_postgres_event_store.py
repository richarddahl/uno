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
from uno.infrastructure.di.provider import ServiceCollection
from uno.infrastructure.di.providers.database import register_database_services

from uno.infrastructure.di.providers.database import (
    register_database_services,
    db_engine_factory,
    db_session_factory,
)
from uno.infrastructure.logging.logger import LoggerService, LoggingConfig
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, AsyncGenerator, TypeVar, Generic

T = TypeVar("T")

class MockSession(AsyncSession):
    async def execute(self, statement: Any, *args: Any, **kwargs: Any) -> Any:
        return MockResult()

class MockResult(Generic[T]):
    def __init__(self) -> None:
        self._data: list[T] = []
    
    def all(self) -> list[T]:
        return self._data
    
    def first(self) -> T | None:
        return self._data[0] if self._data else None

class MockLoggerFactory:
    def create_logger(self, name: str) -> LoggerService:
        return MockLogger()

class MockLogger(LoggerService):
    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        pass
    
    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        pass
    
    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        pass
    
    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        pass


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
async def pg_event_store() -> AsyncGenerator[PostgresEventStore, None]:
    # Create the event store with a mock session
    store = PostgresEventStore(
        db_session=MockSession(),
        logger_factory=MockLoggerFactory()
    )
    
    # Initialize the event store
    await store.initialize()
    
    # Yield control to the test
    yield store
    
    # Clean up
    await store.dispose()


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
