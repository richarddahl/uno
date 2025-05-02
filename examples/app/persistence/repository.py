# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
In-memory event-sourced repository for InventoryItem (example vertical slice).
Replace with a real event store for production/demo persistence.
"""

from typing import Any, Dict
from examples.app.domain.inventory import (
    InventoryItem,
    InventoryItemCreated,
    InventoryItemRenamed,
    InventoryItemAdjusted,
)
from examples.app.api.errors import InventoryItemNotFoundError
from uno.core.errors import Success, Failure
from uno.core.logging import LoggerService


class InMemoryInventoryItemRepository:
    """A minimal in-memory event-sourced repo for InventoryItem."""

    def __init__(self, logger: LoggerService) -> None:
        self._events: dict[str, list[Any]] = {}
        self._logger = logger
        self._logger.debug("InMemoryInventoryItemRepository initialized.")

    def save(
        self, item: InventoryItem | Success | Failure
    ) -> Success[None, None] | Failure[None, Exception]:
        # Unwrap Result if needed
        if hasattr(item, "unwrap"):
            try:
                item = item.unwrap()
            except Exception as e:
                self._logger.error(f"Failed to unwrap Result in save: {e}")
                return Failure(e)
        self._logger.info(f"Saving inventory item: {item.id}")
        # For demo: append all events (in real ES, track new events only)
        self._events.setdefault(item.id, []).extend(item._domain_events)
        item._domain_events.clear()
        self._logger.debug(
            f"Inventory item {item.id} saved with {len(item._domain_events)} events."
        )
        return Success(None)

    def get(
        self, aggregate_id: str
    ) -> Success[InventoryItem, None] | Failure[None, InventoryItemNotFoundError]:
        events = self._events.get(aggregate_id)
        if not events:
            self._logger.warning(f"InventoryItem not found: {aggregate_id}")
            return Failure(InventoryItemNotFoundError(aggregate_id))
        item = None
        for event in events:
            if isinstance(event, InventoryItemCreated):
                item = InventoryItem(
                    id=event.aggregate_id, name=event.name, quantity=event.quantity
                )
            elif isinstance(event, InventoryItemRenamed) and item:
                item.name = event.new_name
            elif isinstance(event, InventoryItemAdjusted) and item:
                item.quantity += event.adjustment
        self._logger.debug(f"Fetched inventory item: {aggregate_id}")
        if item is not None:
            return Success(item)
        else:
            return Failure(InventoryItemNotFoundError(aggregate_id))

    def all_ids(self) -> list[str]:
        ids = list(self._events.keys())
        self._logger.debug(f"Listing all inventory item ids: {ids}")
        return ids
