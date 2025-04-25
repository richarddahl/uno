"""
Unit tests for Uno event-sourced DDD infrastructure.
"""

import asyncio
from typing import Any

import pytest

from uno.core.domain.core import DomainEvent
from uno.core.domain.event_sourced_repository import EventSourcedRepository
from uno.core.events.event_store import EventStore
from uno.core.events.events import EventPublisher, EventPublisherProtocol
from uno.core.logging.logger import LoggerService

# --- Test Fixtures and Mocks ---


class FakeEvent(DomainEvent):
    event_type: str = "test_event"
    value: int


import uuid

from pydantic import BaseModel, Field, PrivateAttr


class FakeAggregateRoot(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    _events: list[DomainEvent] = PrivateAttr(default_factory=list)
    value: int = Field(default=0)

    def add_event(self, event: DomainEvent) -> None:
        if event.aggregate_id and self.id != event.aggregate_id:
            self.id = event.aggregate_id
        self.apply_event(event)
        self._events.append(event)

    def clear_events(self) -> list[DomainEvent]:
        events = self._events.copy()
        self._events.clear()
        return events

    @classmethod
    def from_events(cls, events: list[DomainEvent]):
        if not events:
            return cls()
        obj = cls(id=events[0].aggregate_id)
        for event in events:
            obj.apply_event(event)
        return obj

    def apply_event(self, event: DomainEvent) -> None:
        # This will be overridden in FakeAggregate
        pass


class FakeAggregate(FakeAggregateRoot):
    def apply_test_event(self, event: FakeEvent) -> None:
        self.value += event.value

    def apply_event(self, event: DomainEvent) -> None:
        if isinstance(event, FakeEvent):
            self.apply_test_event(event)


class InMemoryEventStore(EventStore[FakeEvent]):
    def __init__(self):
        self.events: list[FakeEvent] = []

    async def save_event(self, event: FakeEvent) -> None:
        self.events.append(event)

    async def get_events_by_aggregate_id(
        self, aggregate_id: str, event_types: list[str] | None = None
    ) -> list[FakeEvent]:
        return [e for e in self.events if e.aggregate_id == aggregate_id]

    async def get_events_by_type(self, event_type: str, since=None) -> list[FakeEvent]:
        # Return all events for testing, so repository.list() can group by aggregate_id
        return self.events


class DummyPublisher(EventPublisher, EventPublisherProtocol):
    def __init__(self):
        self.published: list[DomainEvent] = []

    async def publish(self, event: DomainEvent) -> None:
        self.published.append(event)


class DummyLogger(LoggerService):
    def __init__(self):
        pass

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        pass

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        pass


@pytest.fixture
def repo_and_store():
    store = InMemoryEventStore()
    publisher = DummyPublisher()
    logger = DummyLogger()
    repo = EventSourcedRepository(
        aggregate_type=FakeAggregate,
        event_store=store,
        event_publisher=publisher,
        logger=logger,
    )
    return repo, store, publisher


# --- Tests ---


def test_aggregate_rehydration():
    events = [
        FakeEvent(event_id="1", aggregate_id="agg1", value=5),
        FakeEvent(event_id="2", aggregate_id="agg1", value=3),
    ]
    agg = FakeAggregate.from_events(events)
    assert agg.id == "agg1"
    assert agg.value == 8


def test_event_application():
    agg = FakeAggregate(id="agg2")
    event = FakeEvent(event_id="3", aggregate_id="agg2", value=7)
    agg.add_event(event)
    assert agg.value == 7
    assert agg.clear_events() == [event]


def test_repository_add_and_get(repo_and_store):
    repo, store, publisher = repo_and_store
    agg = FakeAggregate(id="agg3")
    agg.add_event(FakeEvent(event_id="4", aggregate_id="agg3", value=2))
    asyncio.run(repo.add(agg))
    loaded = asyncio.run(repo.get_by_id("agg3"))
    assert loaded is not None
    assert loaded.id == "agg3"
    assert loaded.value == 2
    # Publisher should have published the event
    assert len(publisher.published) == 1


def test_repository_list(repo_and_store):
    repo, store, publisher = repo_and_store
    agg1 = FakeAggregate(id="agg4")
    agg1.add_event(FakeEvent(event_id="5", aggregate_id="agg4", value=10))
    agg2 = FakeAggregate(id="agg5")
    agg2.add_event(FakeEvent(event_id="6", aggregate_id="agg5", value=20))
    asyncio.run(repo.add(agg1))
    asyncio.run(repo.add(agg2))
    aggs = asyncio.run(repo.list())
    ids = {a.id for a in aggs}
    assert "agg4" in ids and "agg5" in ids
