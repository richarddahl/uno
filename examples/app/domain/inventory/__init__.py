"""
Inventory bounded context: aggregates, events, and value objects for inventory management.

This context is responsible for inventory items, lots, adjustments, and related events.
"""

from .item import (
    InventoryItem,
    InventoryItemCreated,
    InventoryItemRenamed,
    InventoryItemAdjusted,
)
from .lot import (
    InventoryLot,
    InventoryLotCreated,
    InventoryLotAdjusted,
    InventoryLotsCombined,
    InventoryLotSplit,
)

__all__ = [
    "InventoryItem",
    "InventoryItemCreated",
    "InventoryItemRenamed",
    "InventoryItemAdjusted",
    "InventoryLot",
    "InventoryLotCreated",
    "InventoryLotAdjusted",
    "InventoryLotsCombined",
    "InventoryLotSplit",
]
