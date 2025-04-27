# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
In-memory repository for Order aggregates (example/demo only).
"""
import hashlib
from typing import cast
from examples.app.domain.order import Order
from uno.core.logging import LoggerService

class InMemoryOrderRepository:
    def __init__(self, logger: LoggerService) -> None:
        self._orders: dict[str, Order] = {}
        self._event_hashes: dict[str, list[str]] = {}  # order_id -> list of event hashes
        self._logger = logger
        self._logger.debug("InMemoryOrderRepository initialized.")

    def get(self, order_id: str) -> Success | Failure:
        order = self._orders.get(order_id)
        if order is None:
            return Failure(OrderNotFoundError(order_id))
        self._logger.debug(f"Fetching order with id: {order_id} - Found: {order is not None}")
        return Success(order)

    def save(self, order: Order) -> None:
        self._orders[order.id] = order
        self._logger.info(f"Saving order: {order.id}")
        # Hash chain: hash each event with previous hash
        events = getattr(order, '_domain_events', [])
        hashes = self._event_hashes.get(order.id, [])
        prev_hash = hashes[-1] if hashes else ''
        for event in events[len(hashes):]:
            event_bytes = str(event.model_dump(exclude_none=True, exclude_unset=True, by_alias=True)).encode()
            h = hashlib.sha256(prev_hash.encode() + event_bytes).hexdigest()
            hashes.append(h)
            prev_hash = h
        self._event_hashes[order.id] = hashes
        self._logger.debug(f"Order {order.id} saved with {len(events)} events.")

    def all_ids(self) -> list[str]:
        ids = list(self._orders.keys())
        self._logger.debug(f"Listing all order ids: {ids}")
        return ids

    def verify_integrity(self, order_id: str) -> bool:
        order = self._orders.get(order_id)
        if order is None:
            self._logger.warning(f"Order not found for integrity check: {order_id}")
            return False
        events = getattr(order, '_domain_events', [])
        hashes = self._event_hashes.get(order_id, [])
        prev_hash = ''
        for i, event in enumerate(events):
            event_bytes = str(event.model_dump(exclude_none=True, exclude_unset=True, by_alias=True)).encode()
            h = hashlib.sha256(prev_hash.encode() + event_bytes).hexdigest()
            if i >= len(hashes) or hashes[i] != h:
                self._logger.error(f"Integrity check failed for order {order_id} at event {i}")
                return False
            prev_hash = h
        self._logger.info(f"Integrity check passed for order {order_id}")
        return True
