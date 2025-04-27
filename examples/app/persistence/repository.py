# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
In-memory event-sourced repository for InventoryItem (example vertical slice).
Replace with a real event store for production/demo persistence.
"""
from typing import Any, Dict
from examples.app.domain.inventory_item import InventoryItem, InventoryItemCreated, InventoryItemRenamed, InventoryItemAdjusted

class InMemoryInventoryItemRepository:
    """A minimal in-memory event-sourced repo for InventoryItem."""
    def __init__(self) -> None:
        self._events: dict[str, list[Any]] = {}

    def save(self, item: InventoryItem) -> None:
        # For demo: append all events (in real ES, track new events only)
        self._events.setdefault(item.id, []).extend(item._domain_events)
        item._domain_events.clear()

    def get(self, item_id: str) -> InventoryItem | None:
        events = self._events.get(item_id)
        if not events:
            return None
        item = None
        for event in events:
            if isinstance(event, InventoryItemCreated):
                item = InventoryItem(id=event.item_id, name=event.name, quantity=event.quantity)
            elif isinstance(event, InventoryItemRenamed) and item:
                item.name = event.new_name
            elif isinstance(event, InventoryItemAdjusted) and item:
                item.quantity += event.adjustment
        return item

    def all_ids(self) -> list[str]:
        return list(self._events.keys())
