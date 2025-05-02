# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Tests for Uno event upcasting and upcaster registry usage.
Demonstrates how to register upcasters and verify event migration across versions.
"""

import pytest
from typing import Any


# Simulate canonical event base and upcaster registry (replace with actual Uno imports as needed)
class DomainEvent:
    version: int = 1

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def model_dump(self) -> dict[str, Any]:
        return dict(self.__dict__)

    @classmethod
    def upcast(cls, data: dict[str, Any]) -> "DomainEvent":
        # Stub for upcasting logic, will be replaced by registry
        return cls(**data)


# Upcaster registry pattern
UPCASTERS: dict[tuple[type, int], Any] = {}


def register_upcaster(event_type: type, from_version: int):
    def decorator(func):
        UPCASTERS[(event_type, from_version)] = func
        return func

    return decorator


def apply_upcasters(
    event_type: type, data: dict[str, Any], from_version: int, to_version: int
) -> dict[str, Any]:
    v = from_version
    while v < to_version:
        upcaster = UPCASTERS.get((event_type, v))
        if not upcaster:
            raise ValueError(f"No upcaster for {event_type.__name__} v{v} -> v{v + 1}")
        data = upcaster(data)
        v += 1
    return data


# Example event evolution
class InventoryCreatedV1(DomainEvent):
    version = 1

    def __init__(self, aggregate_id: str, name: str):
        super().__init__(aggregate_id=aggregate_id, name=name)


class InventoryCreatedV2(DomainEvent):
    version = 2

    def __init__(self, aggregate_id: str, name: str, sku: str):
        super().__init__(aggregate_id=aggregate_id, name=name, sku=sku)


@register_upcaster(InventoryCreatedV2, 1)
def upcast_inventory_created_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    # Add sku field with default value
    data = dict(data)
    data["sku"] = f"SKU-{data['aggregate_id']}"
    return data


@pytest.mark.parametrize(
    "from_version,event_type,from_data,to_version,to_event_cls,expected",
    [
        (
            1,
            InventoryCreatedV2,
            {"aggregate_id": "abc", "name": "Widget"},
            2,
            InventoryCreatedV2,
            {"aggregate_id": "abc", "name": "Widget", "sku": "SKU-abc"},
        ),
    ],
)
def test_event_upcasting(
    from_version, event_type, from_data, to_version, to_event_cls, expected
):
    upcasted_data = apply_upcasters(event_type, from_data, from_version, to_version)
    event = to_event_cls(**upcasted_data)
    assert event.model_dump() == expected


def test_upcaster_registry_missing():
    # Should raise if no upcaster is registered for a version jump
    with pytest.raises(ValueError):
        apply_upcasters(
            InventoryCreatedV2, {"aggregate_id": "abc", "name": "Widget"}, 1, 3
        )


def test_idempotent_upcast():
    # Upcasting from v2 to v2 should be a no-op
    data = {"aggregate_id": "abc", "name": "Widget", "sku": "SKU-abc"}
    result = apply_upcasters(InventoryCreatedV2, data, 2, 2)
    assert result == data


"""
USAGE EXAMPLE:

# Register an upcaster for an event type and version
@register_upcaster(MyEventV2, 1)
def upcast_my_event_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    data = dict(data)
    data['new_field'] = 'default'
    return data

# Apply upcasters to migrate event data
migrated = apply_upcasters(MyEventV2, old_event_data, from_version=1, to_version=2)
new_event = MyEventV2(**migrated)
"""
