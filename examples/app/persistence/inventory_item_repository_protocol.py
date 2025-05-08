# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Repository protocol for InventoryItem (Uno example app).
Defines the interface for all InventoryItem repository implementations.
"""

from typing import Protocol, runtime_checkable
from uno.errors.result import Success, Failure
from examples.app.domain.inventory import InventoryItem
from examples.app.api.errors import InventoryItemNotFoundError


@runtime_checkable
class InventoryItemRepository(Protocol):
    def save(
        self, item: InventoryItem
    ) -> Success[None, None] | Failure[None, Exception]: ...
    def get(
        self, aggregate_id: str
    ) -> Success[InventoryItem, None] | Failure[None, InventoryItemNotFoundError]:
        """
        Retrieve an inventory item by id. Returns Success[InventoryItem, None] if found, Failure[None, InventoryItemNotFoundError] if not found.
        """
        ...

    def all_ids(self) -> list[str]: ...
