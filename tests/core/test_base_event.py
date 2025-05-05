"""
Unit tests for uno.core.base_event: event versioning, upcasting, and hash chaining.
Coverage: 100% of DomainEvent and EventUpcasterRegistry logic.
"""

from typing import Any, ClassVar

import pytest

from uno.core.events.base_event import (
    DomainEvent,
    EventUpcasterRegistry,
    verify_event_stream_integrity,
)


class FakeEventV1(DomainEvent):
    version: int = 1
    __version__: ClassVar[int] = 1
    foo: str


class FakeEventV2(DomainEvent):
    version: int = 2
    __version__: ClassVar[int] = 2
    foo: str
    bar: int = 0


# --- Upcaster for v1 -> v2 ---
def upcast_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    data = dict(data)
    data["bar"] = 42
    data["version"] = 2  # Always set the new version explicitly
    return data


EventUpcasterRegistry.register_upcaster(FakeEventV2, 1, upcast_v1_to_v2)


def upcast_v1_to_v2(data: dict[str, object]) -> dict[str, object]:
    data = dict(data)
    data["bar"] = 42
    data["version"] = 2
    return data


def test_event_upcasting() -> None:
    # Register upcaster for FakeEventV2 v1 -> v2
    EventUpcasterRegistry._registry.clear()
    EventUpcasterRegistry.register_upcaster(FakeEventV2, 1, upcast_v1_to_v2)
    v1_data = {"event_id": "evt_123", "foo": "hello", "version": 1}
    # Upcast the dict before constructing
    upcasted = EventUpcasterRegistry.apply(FakeEventV2, v1_data, 1, 2)
    result = FakeEventV2.from_dict(upcasted)
    assert hasattr(result, "unwrap"), f"Expected Result, got {type(result)}"
    event = result.unwrap()
    assert event.foo == "hello"
    assert event.bar == 42
    assert event.version == 2


def test_event_hash_and_chain() -> None:
    # Create a chain of events with deterministic fields
    e1 = FakeEventV2(
        event_id="evt_1", foo="a", bar=1, previous_hash=None, timestamp=1.0
    )
    e2 = FakeEventV2(
        event_id="evt_2", foo="b", bar=2, previous_hash=e1.event_hash, timestamp=2.0
    )
    e3 = FakeEventV2(
        event_id="evt_3", foo="c", bar=3, previous_hash=e2.event_hash, timestamp=3.0
    )
    # Chain is valid
    assert verify_event_stream_integrity([e1, e2, e3])
    # Tamper with e2
    e2_tampered = FakeEventV2(
        event_id="evt_2",
        foo="tampered",
        bar=2,
        previous_hash=e1.event_hash,
        event_hash=e2.event_hash,
        timestamp=2.0,
    )
    with pytest.raises(ValueError, match="previous_hash does not match"):
        verify_event_stream_integrity([e1, e2_tampered, e3])


def test_event_hash_is_deterministic() -> None:
    e1 = FakeEventV2(
        event_id="evt_x", foo="z", bar=7, previous_hash=None, timestamp=42.0
    )
    e2 = FakeEventV2(
        event_id="evt_x", foo="z", bar=7, previous_hash=None, timestamp=42.0
    )
    assert e1.event_hash == e2.event_hash


def test_upcaster_registry_missing() -> None:
    # No upcaster for v2 -> v3
    class FakeEventV3(DomainEvent):
        version: int = 3
        __version__: ClassVar[int] = 3
        foo: str
        bar: int
        baz: str

    v2_data = {"event_id": "evt_999", "foo": "hi", "bar": 1, "version": 2}
    from uno.core.errors.definitions import EventUpcastError

    from uno.core.errors.result import Failure

    result = FakeEventV3.from_dict(v2_data)
    assert isinstance(result, Failure)
    assert isinstance(result.error, Exception)
