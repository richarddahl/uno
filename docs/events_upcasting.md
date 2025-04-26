# Event Upcasting & Migration Example: Bourbon Distillery Inventory

This example demonstrates Uno's canonical approach to event versioning and upcasting, using a realistic domain: inventory management for a bourbon distillery (corn, malted barley, rye, wheat, yeast, etc).

## Motivation

As your event schema evolves, older events must be transparently migrated to the latest version for validation and processing. Uno supports this via an upcaster registry and versioned event models.

## Example: InventoryAdded Event Evolution

### Version History
- **V1:** `item_name`, `quantity` (as `decimal.Decimal`)
- **V2:** Adds `unit` (e.g., kg, lb)
- **V3:** Adds `supplier` (traceability)

### Defining Versioned Events
```python
from decimal import Decimal
from uno.core.events.base_event import DomainEvent

class InventoryAddedV1(DomainEvent):
    __version__ = 1
    item_name: str
    quantity: Decimal

class InventoryAddedV2(DomainEvent):
    __version__ = 2
    item_name: str
    quantity: Decimal
    unit: str

class InventoryAddedV3(DomainEvent):
    __version__ = 3
    item_name: str
    quantity: Decimal
    unit: str
    supplier: str
```

### Registering Upcasters
```python
from uno.core.events.base_event import EventUpcasterRegistry

def upcast_v1_to_v2(data: dict) -> dict:
    data = dict(data)
    data["unit"] = "kg"
    return data

def upcast_v2_to_v3(data: dict) -> dict:
    data = dict(data)
    data["supplier"] = "Unknown"
    return data

EventUpcasterRegistry.register(InventoryAddedV2, from_version=1, upcaster=upcast_v1_to_v2)
EventUpcasterRegistry.register(InventoryAddedV3, from_version=2, upcaster=upcast_v2_to_v3)
```

### Usage: Upcasting Legacy Events
```python
from decimal import Decimal
legacy_v1 = {"item_name": "corn", "quantity": Decimal("1000.0"), "version": 1}
event = InventoryAddedV3.from_dict(legacy_v1)
assert event.unit == "kg"
assert event.supplier == "Unknown"
```

### Test Case
```python
import pytest
from decimal import Decimal
from uno.core.errors.definitions import EventUpcastError

def test_inventory_added_upcasting():
    v1_data = {"item_name": "rye", "quantity": Decimal("500.0"), "version": 1}
    event = InventoryAddedV3.from_dict(v1_data)
    assert event.unit == "kg"
    assert event.supplier == "Unknown"

    v2_data = {"item_name": "yeast", "quantity": Decimal("10.0"), "unit": "g", "version": 2}
    event = InventoryAddedV3.from_dict(v2_data)
    assert event.unit == "g"
    assert event.supplier == "Unknown"

    v3_data = {"item_name": "malted barley", "quantity": Decimal("200.0"), "unit": "kg", "supplier": "BestGrains", "version": 3}
    event = InventoryAddedV3.from_dict(v3_data)
    assert event.unit == "kg"
    assert event.supplier == "BestGrains"

    v0_data = {"item_name": "wheat", "quantity": Decimal("100.0"), "version": 0}
    with pytest.raises(EventUpcastError):
        InventoryAddedV3.from_dict(v0_data)

# This test covers upcasting from all supported versions and verifies that missing upcasters raise the correct error.
        InventoryAddedV3.from_dict(v0_data)
```

---

**See also:**
- `examples/inventory_upcasting.py` (runnable usage example)
- `tests/core/test_base_event.py` (unit test)
- Uno event upcasting API reference
