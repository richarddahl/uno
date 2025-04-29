# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Repository protocol for InventoryItem (Uno example app).
Defines the interface for all InventoryItem repository implementations.
"""

from typing import Protocol
from uno.core.errors.result import Success, Failure
from examples.app.domain.inventory import InventoryItem
from examples.app.api.errors import InventoryItemNotFoundError


class InventoryItemRepository(Protocol):
    def save(self, item: InventoryItem) -> None: ...
    def get(
        self, item_id: str
    ) -> Success[InventoryItem, None] | Failure[None, InventoryItemNotFoundError]: ...
    def all_ids(self) -> list[str]: ...
