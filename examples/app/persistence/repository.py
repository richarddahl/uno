# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
In-memory event-sourced repository for InventoryItem (example vertical slice).
Replace with a real event store for production/demo persistence.
"""


from typing import Any

from examples.app.domain.inventory import (
    InventoryItem,
    InventoryItemAdjusted,
    InventoryItemCreated,
    InventoryItemRenamed,
)
from examples.app.api.errors import InventoryItemNotFoundError

from uno.logging import LoggerProtocol


class InMemoryInventoryItemRepository:
    """A minimal in-memory event-sourced repo for InventoryItem."""

    def __init__(self, logger: LoggerProtocol) -> None:
        self._events: dict[str, list[Any]] = {}
        self._logger = logger
        self._logger.debug("InMemoryInventoryItemRepository initialized.")

    def save(
        self, item: InventoryItem
    ) -> None:
        self._logger.info(f"Saving inventory item: {item.id}")
        # For demo: append all events (in real ES, track new events only)
        self._events.setdefault(item.id, []).extend(item._domain_events)
        item._domain_events.clear()
        self._logger.debug(
            f"Inventory item {item.id} saved with {len(item._domain_events)} events."
        )

    def get(
        self, aggregate_id: str
    ) -> InventoryItem:
        events = self._events.get(aggregate_id)
        if not events:
            self._logger.warning(f"InventoryItem not found: {aggregate_id}")
            raise InventoryItemNotFoundError(aggregate_id)
        item = None
        for event in events:
            if isinstance(event, InventoryItemCreated):
                item = InventoryItem(
                    event.aggregate_id, event.name, event.measurement
                )
            elif isinstance(event, InventoryItemRenamed) and item:
                item.name = event.new_name
            elif isinstance(event, InventoryItemAdjusted) and item:
                item.measurement += event.adjustment
        self._logger.debug(f"Fetched inventory item: {aggregate_id}")
        if item is not None:
            return item
        else:
            raise InventoryItemNotFoundError(aggregate_id)

    def all_ids(self) -> list[str]:
        ids = list(self._events.keys())
        self._logger.debug(f"Listing all inventory item ids: {ids}")
        return ids
