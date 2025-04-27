# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
In-memory repository for InventoryLot aggregates (example/demo only).
"""
from examples.app.domain.inventory_lot import InventoryLot
from typing import Dict

class InMemoryInventoryLotRepository:
    def __init__(self) -> None:
        self._lots: Dict[str, InventoryLot] = {}

    def get(self, lot_id: str) -> InventoryLot | None:
        return self._lots.get(lot_id)

    def save(self, lot: InventoryLot) -> None:
        self._lots[lot.id] = lot

    def all_ids(self) -> list[str]:
        return list(self._lots.keys())
