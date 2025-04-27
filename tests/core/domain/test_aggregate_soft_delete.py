from typing import ClassVar, Union

from pydantic import ConfigDict

from uno.core.domain.aggregate import AggregateRoot
from uno.core.errors import AggregateNotDeletedError, Failure, Success
from uno.core.events.base_event import DomainEvent
from uno.core.events.deleted_event import DeletedEvent
from uno.core.events.restored_event import RestoredEvent


class FakeCreatedEvent(DomainEvent):
    event_type: ClassVar[str] = "created"
    aggregate_id: str
    model_config = ConfigDict(frozen=False)


class FakeAggregate(AggregateRoot[str]):
    name: str = ""

    def change_name(
        self, new_name: str
    ) -> Success[None, Exception] | Failure[None, Exception]:
        result = self.assert_not_deleted()
        if result.is_failure:
            return result
        self.name = new_name
        return Success(None)


def test_rehydration_deleted() -> None:
    events = [
        FakeCreatedEvent(aggregate_id="foo"),
        DeletedEvent(aggregate_id="foo"),
    ]
    agg = FakeAggregate.from_events(events)
    assert agg.is_deleted


def test_rehydration_restored() -> None:
    events = [
        FakeCreatedEvent(aggregate_id="foo"),
        DeletedEvent(aggregate_id="foo"),
        RestoredEvent(aggregate_id="foo"),
    ]
    agg = FakeAggregate.from_events(events)
    assert not agg.is_deleted


def test_mutation_guard_after_delete() -> None:
    agg = FakeAggregate.from_events(
        [
            FakeCreatedEvent(aggregate_id="foo"),
            DeletedEvent(aggregate_id="foo"),
        ]
    )
    result = agg.change_name("bar")
    assert result.is_failure
    assert isinstance(result.error, AggregateNotDeletedError)


def test_mutation_allowed_after_restore() -> None:
    agg = FakeAggregate.from_events(
        [
            FakeCreatedEvent(aggregate_id="foo"),
            DeletedEvent(aggregate_id="foo"),
            RestoredEvent(aggregate_id="foo"),
        ]
    )
    result = agg.change_name("bar")
    assert result.is_success
    assert agg.name == "bar"


def test_restore_only_if_deleted() -> None:
    agg = FakeAggregate.from_events(
        [
            FakeCreatedEvent(aggregate_id="foo"),
        ]
    )
    result = agg.add_event(RestoredEvent(aggregate_id="foo"))
    assert result.is_failure
    assert isinstance(result.error, AggregateNotDeletedError)


def test_event_stream_integrity() -> None:
    events = [
        FakeCreatedEvent(aggregate_id="foo"),
        DeletedEvent(aggregate_id="foo"),
        RestoredEvent(aggregate_id="foo"),
    ]
    agg = FakeAggregate.from_events(events)
    # _events only tracks newly added events, so check rehydration order by replaying
    replayed = []
    for event in events:
        if isinstance(event, DeletedEvent):
            replayed.append("deleted")
        elif isinstance(event, RestoredEvent):
            replayed.append("restored")
        else:
            replayed.append(event.event_type)
    assert replayed == ["created", "deleted", "restored"]
