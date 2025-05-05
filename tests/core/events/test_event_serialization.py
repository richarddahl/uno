import pytest
from uno.core.events.base_event import DomainEvent
from pydantic import Field
import json


class ExampleEvent(DomainEvent):
    aggregate_id: str
    value: int = Field(...)
    extra: str | None = None


def test_event_serialization_is_deterministic():
    event1 = ExampleEvent(aggregate_id="agg-1", value=42, extra=None)
    event2 = ExampleEvent(aggregate_id="agg-1", value=42)  # extra omitted

    # Canonical serialization: use to_dict with sort_keys
    dict1 = event1.to_dict()
    dict2 = event2.to_dict()
    json1 = json.dumps(dict1, sort_keys=True)
    json2 = json.dumps(dict2, sort_keys=True)

    # Should be identical regardless of field order or unset/None fields
    assert json1 == json2

    # Hash should be identical as well
    assert event1.event_hash == event2.event_hash

    # Changing a value should change both serialization and hash
    event3 = ExampleEvent(aggregate_id="agg-1", value=99)
    dict3 = event3.to_dict()
    json3 = json.dumps(dict3, sort_keys=True)
    assert json3 != json1
    assert event3.event_hash != event1.event_hash


def test_event_to_dict_roundtrip():
    event = ExampleEvent(aggregate_id="agg-2", value=123, extra="foo")
    data = event.to_dict()
    # Simulate persistence and retrieval
    # Use from_dict to reconstruct
    result = ExampleEvent.from_dict(data)
    assert result.is_success, f"from_dict failed: {result.error}"
    restored = result.unwrap()
    assert restored.to_dict() == data
    assert restored.aggregate_id == event.aggregate_id
    assert restored.value == event.value
    assert restored.extra == event.extra
    # Ensure version is preserved if present
    if hasattr(event, "version"):
        assert getattr(restored, "version", None) == getattr(event, "version", None)
