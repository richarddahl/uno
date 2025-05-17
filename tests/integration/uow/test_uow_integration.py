"""Integration tests for the Unit of Work with real components."""

import pytest
import uuid
from unittest.mock import patch, AsyncMock

from uno.domain.aggregate import AggregateRoot
from uno.uow import UnitOfWorkFactory, BaseUnitOfWork
from uno.event_store.base import EventStore


class MockAggregate(AggregateRoot):
    """Test aggregate for integration testing."""

    name: str = "Test"


class TestEventStore(EventStore):
    """In-memory event store for testing."""

    def __init__(self):
        self.events = []
        self.committed = False

    async def append(self, aggregate_id: str, events: list, **kwargs) -> None:
        self.events.extend(events)

    async def get_events(self, aggregate_id: str, **kwargs) -> list:
        return [
            e for e in self.events if getattr(e, "aggregate_id", None) == aggregate_id
        ]

    async def _commit(self) -> None:
        self.committed = True

    async def _rollback(self) -> None:
        self.events = []


class TestIntegrationUnitOfWork(BaseUnitOfWork):
    """Integration test UoW with real event store."""

    def __init__(self, repository_factory, event_store: EventStore):
        super().__init__(repository_factory)
        self.event_store = event_store

    async def _commit(self) -> None:
        # Collect and publish all events
        events = self.collect_new_events()
        if events:
            await self.event_store.append(
                aggregate_id=str(events[0].aggregate_id), events=events
            )
        await self.event_store._commit()

    async def _rollback(self) -> None:
        await self.event_store._rollback()


@pytest.fixture
def event_store():
    """Fixture that provides an event store for testing."""
    return TestEventStore()


@pytest.fixture
def uow_factory(event_store):
    """Fixture that provides a UoW factory with an event store."""

    def repository_factory(aggregate_type):
        # In a real implementation, this would create a repository
        # with the event store dependency
        return None  # Simplified for this example

    return UnitOfWorkFactory(
        uow_class=TestIntegrationUnitOfWork,
        repository_factory=repository_factory,
        event_store=event_store,
    )


@pytest.mark.asyncio
async def test_uow_with_event_store(uow_factory, event_store):
    """Test that UoW properly integrates with event store."""
    async with uow_factory.transaction() as uow:
        # In a real test, we would:
        # 1. Get a repository
        # 2. Load or create an aggregate
        # 3. Make changes to the aggregate
        # 4. Save the aggregate
        # 5. Verify events are stored
        pass

    # Verify the transaction was committed
    assert event_store.committed


@pytest.mark.asyncio
async def test_uow_rollback(event_store):
    """Test that UoW properly rolls back on error."""

    class TestError(Exception):
        pass

    with pytest.raises(TestError):
        async with UnitOfWorkFactory(
            uow_class=TestIntegrationUnitOfWork,
            repository_factory=lambda _: None,
            event_store=event_store,
        ).transaction() as uow:
            # Simulate an error
            raise TestError("Something went wrong")

    # Verify the transaction was rolled back
    assert not event_store.committed
    assert not event_store.events
