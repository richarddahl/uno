# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
In-memory repository for Order aggregates (example/demo only).
"""
from examples.app.domain.order import Order
from typing import Dict

class InMemoryOrderRepository:
    def __init__(self) -> None:
        self._orders: Dict[str, Order] = {}

    def get(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)

    def save(self, order: Order) -> None:
        self._orders[order.id] = order

    def all_ids(self) -> list[str]:
        return list(self._orders.keys())
