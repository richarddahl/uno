"""
Tests for EventUpcasterRegistry usage and upcaster application in Uno.
"""

import pytest
from pydantic import ValidationError
from uno.core.events.base_event import DomainEvent, EventUpcasterRegistry
from uno.core.errors.definitions import EventUpcastError


class LegacyEventV1(DomainEvent):
    version: int = 1
    foo: str


from typing import ClassVar


class LegacyEventV2(DomainEvent):
    version: int = 2
    __version__: ClassVar[int] = 2
    foo: str
    bar: int


from uno.core.errors.definitions import EventUpcastError

BAR_MAGIC_VALUE = 42
LATEST_VERSION = 2


def upcast_v1_to_v2(data: dict[str, object]) -> dict[str, object]:
    """Upcaster: adds 'bar' field and bumps version."""
    data = dict(data)
    data["bar"] = BAR_MAGIC_VALUE
    data["version"] = LATEST_VERSION
    return data


def test_upcaster_registry_applies_chain() -> None:
    """Should upcast v1 dict to v2 event with all required fields."""
    EventUpcasterRegistry._registry.clear()
    EventUpcasterRegistry.register_upcaster(LegacyEventV2, 1, upcast_v1_to_v2)
    legacy_v1: dict[str, object] = {"foo": "bar", "version": 1}
    # Upcast the dict before constructing
    upcasted = EventUpcasterRegistry.apply(LegacyEventV2, legacy_v1, 1, LATEST_VERSION)
    result = LegacyEventV2.from_dict(upcasted)
    assert hasattr(result, "unwrap"), f"Expected Result, got {type(result)}"
    event = result.unwrap()
    assert event.bar == BAR_MAGIC_VALUE
    assert event.version == LATEST_VERSION


def test_upcaster_registry_missing_upcaster() -> None:
    """Should raise EventUpcastError or ValidationError if no upcaster is registered."""
    EventUpcasterRegistry._registry.clear()
    legacy_v1: dict[str, object] = {"foo": "bar", "version": 1}
    from uno.core.errors.result import Failure

    result = LegacyEventV2.from_dict(legacy_v1)
    assert isinstance(result, Failure)
    assert isinstance(result.error, Exception)
