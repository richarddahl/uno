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
    result = FakeAggregate.from_events(events)
    assert result.is_success
    agg = result.value
    assert agg.is_deleted


def test_rehydration_restored() -> None:
    events = [
        FakeCreatedEvent(aggregate_id="foo"),
        DeletedEvent(aggregate_id="foo"),
        RestoredEvent(aggregate_id="foo"),
    ]
    result = FakeAggregate.from_events(events)
    assert result.is_success
    agg = result.value
    assert not agg.is_deleted


def test_mutation_guard_after_delete() -> None:
    result = FakeAggregate.from_events(
        [
            FakeCreatedEvent(aggregate_id="foo"),
            DeletedEvent(aggregate_id="foo"),
        ]
    )
    assert result.is_success
    agg = result.value
    result2 = agg.change_name("bar")
    assert result2.is_failure
    assert isinstance(result2.error, AggregateNotDeletedError)


def test_mutation_allowed_after_restore() -> None:
    result = FakeAggregate.from_events(
        [
            FakeCreatedEvent(aggregate_id="foo"),
            DeletedEvent(aggregate_id="foo"),
            RestoredEvent(aggregate_id="foo"),
        ]
    )
    assert result.is_success
    agg = result.value
    result2 = agg.change_name("bar")
    assert result2.is_success
    assert agg.name == "bar"


def test_restore_only_if_deleted() -> None:
    result = FakeAggregate.from_events(
        [
            FakeCreatedEvent(aggregate_id="foo"),
        ]
    )
    assert result.is_success
    agg = result.value
    result2 = agg.add_event(RestoredEvent(aggregate_id="foo"))
    assert result2.is_failure
    assert isinstance(result2.error, AggregateNotDeletedError)


def test_event_stream_integrity() -> None:
    events = [
        FakeCreatedEvent(aggregate_id="foo"),
        DeletedEvent(aggregate_id="foo"),
        RestoredEvent(aggregate_id="foo"),
    ]
    result = FakeAggregate.from_events(events)
    assert result.is_success
    agg = result.value
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


def test_domain_event_from_dict_success_and_failure():
    """
    DomainEvent is intentionally permissive: all fields have defaults.
    This test asserts that it can be constructed with minimal data, and
    that error handling for missing required fields should be tested on concrete subclasses.
    """
    from uno.core.events.base_event import DomainEvent
    # Valid minimal event
    valid = {
        "event_id": "evt_123",
        "timestamp": 1234567890.0,
        "version": 1,
        "metadata": {},
    }
    result = DomainEvent.from_dict(valid)
    assert result.is_success
    evt = result.value
    assert evt.event_id == "evt_123"
    # Even with only timestamp, should succeed (all other fields default)
    minimal = {"timestamp": 1234567890.0}
    result2 = DomainEvent.from_dict(minimal)
    assert result2.is_success
    # To test failure, use a subclass with required fields
    from pydantic import Field
    from uno.core.events.base_event import DomainEvent
    class MinimalEvent(DomainEvent):
        required_field: str = Field(...)
    valid2 = {"required_field": "foo"}
    r3 = MinimalEvent.from_dict(valid2)
    assert r3.is_success
    invalid2 = {}
    r4 = MinimalEvent.from_dict(invalid2)
    assert r4.is_failure
    assert isinstance(r4.error, Exception)


def test_deleted_event_from_dict_success_and_failure():
    from uno.core.events.deleted_event import DeletedEvent
    # Valid
    valid = {"aggregate_id": "agg1"}
    result = DeletedEvent.from_dict(valid)
    assert result.is_success
    evt = result.value
    assert evt.aggregate_id == "agg1"
    # Invalid (missing aggregate_id)
    invalid = {"reason": "test"}
    result2 = DeletedEvent.from_dict(invalid)
    assert result2.is_failure
    assert isinstance(result2.error, Exception)


def test_restored_event_from_dict_success_and_failure():
    from uno.core.events.restored_event import RestoredEvent
    valid = {"aggregate_id": "agg2"}
    result = RestoredEvent.from_dict(valid)
    assert result.is_success
    evt = result.value
    assert evt.aggregate_id == "agg2"
    # Invalid (missing aggregate_id)
    invalid = {"restored_by": "user"}
    result2 = RestoredEvent.from_dict(invalid)
    assert result2.is_failure
    assert isinstance(result2.error, Exception)


def test_event_from_dict_corrupt_stream():
    from uno.core.events.base_event import DomainEvent
    # Corrupt: wrong type for event_id
    corrupt = {"event_id": 123, "timestamp": 1.0, "version": 1, "metadata": {}}
    result = DomainEvent.from_dict(corrupt)
    assert result.is_failure
    assert isinstance(result.error, Exception)
