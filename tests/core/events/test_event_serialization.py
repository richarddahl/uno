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

    # Canonical serialization: use model_dump with sort_keys
    dict1 = event1.model_dump(by_alias=True, exclude_unset=True, exclude_none=True)
    dict2 = event2.model_dump(by_alias=True, exclude_unset=True, exclude_none=True)
    json1 = json.dumps(dict1, sort_keys=True)
    json2 = json.dumps(dict2, sort_keys=True)

    # Should be identical regardless of field order or unset/None fields
    assert json1 == json2

    # Hash should be identical as well
    assert event1.event_hash == event2.event_hash

    # Changing a value should change both serialization and hash
    event3 = ExampleEvent(aggregate_id="agg-1", value=99)
    dict3 = event3.model_dump(by_alias=True, exclude_unset=True, exclude_none=True)
    json3 = json.dumps(dict3, sort_keys=True)
    assert json3 != json1
    assert event3.event_hash != event1.event_hash
