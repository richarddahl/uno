"""
Uno Inventory Management Event Upcasting Example (Bourbon Distillery)

Demonstrates event versioning and upcasting for inventory events involving grains and yeast.
"""

from uno.core.events.base_event import DomainEvent, EventUpcasterRegistry


# Version 1: Only item_name and measurement
class InventoryAddedV1(DomainEvent):
    __version__ = 1
    item_name: str
    measurement: float


# Version 2: Adds unit
class InventoryAddedV2(DomainEvent):
    __version__ = 2
    item_name: str
    measurement: float
    unit: str


# Version 3: Adds supplier
class InventoryAddedV3(DomainEvent):
    __version__ = 3
    item_name: str
    measurement: float
    unit: str
    supplier: str


# Upcaster: V1 -> V2


def upcast_v1_to_v2(data: dict) -> dict:
    data = dict(data)
    data["unit"] = "kg"
    return data


# Upcaster: V2 -> V3


def upcast_v2_to_v3(data: dict) -> dict:
    data = dict(data)
    data["supplier"] = "Unknown"
    return data


EventUpcasterRegistry.register(
    InventoryAddedV2, from_version=1, upcaster=upcast_v1_to_v2
)
EventUpcasterRegistry.register(
    InventoryAddedV3, from_version=2, upcaster=upcast_v2_to_v3
)

# Usage: Upcasting from legacy data
legacy_v1 = {"item_name": "corn", "measurement": 1000.0, "version": 1}
event = InventoryAddedV3.from_dict(legacy_v1)
assert event.unit == "kg"
assert event.supplier == "Unknown"
print(f"Upcasted event: {event.model_dump()}")
