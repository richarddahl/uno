# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
In-memory repository for InventoryLot aggregates (example/demo only).
"""

import hashlib
from examples.app.domain.inventory import InventoryLot
from examples.app.api.errors import InventoryLotNotFoundError

from uno.logging import LoggerProtocol


class InMemoryInventoryLotRepository:
    def __init__(self, logger: LoggerProtocol) -> None:
        self._lots: dict[str, InventoryLot] = {}
        self._event_hashes: dict[str, list[str]] = {}  # lot_id -> list of event hashes
        self._logger = logger
        self._logger.debug("InMemoryInventoryLotRepository initialized.")

    def get(
        self, lot_id: str
    ) -> InventoryLot:
        lot = self._lots.get(lot_id)
        if lot is None:
            self._logger.warning(f"InventoryLot not found: {lot_id}")
            raise InventoryLotNotFoundError(lot_id)
        self._logger.debug(f"Fetching lot with id: {lot_id} - Found: {lot is not None}")
        return lot

    def save(self, lot: InventoryLot) -> None:
        self._lots[lot.id] = lot
        self._logger.info(f"Saving lot: {lot.id}")
        # Hash chain: hash each event with previous hash
        events = getattr(lot, "_domain_events", [])
        hashes = self._event_hashes.get(lot.id, [])
        prev_hash = hashes[-1] if hashes else ""
        for event in events[len(hashes) :]:
            event_bytes = str(event.to_dict()).encode()
            h = hashlib.sha256(prev_hash.encode() + event_bytes).hexdigest()
            hashes.append(h)
            prev_hash = h
        self._event_hashes[lot.id] = hashes
        self._logger.debug(f"Lot {lot.id} saved with {len(events)} events.")

    def all_ids(self) -> list[str]:
        ids = list(self._lots.keys())
        self._logger.debug(f"Listing all lot ids: {ids}")
        return ids

    def verify_integrity(self, lot_id: str) -> bool:
        lot = self._lots.get(lot_id)
        if lot is None:
            self._logger.warning(f"Lot not found for integrity check: {lot_id}")
            return False
        events = getattr(lot, "_domain_events", [])
        hashes = self._event_hashes.get(lot_id, [])
        prev_hash = ""
        for i, event in enumerate(events):
            event_bytes = str(event.to_dict()).encode()
            h = hashlib.sha256(prev_hash.encode() + event_bytes).hexdigest()
            if i >= len(hashes) or hashes[i] != h:
                self._logger.error(
                    f"Integrity check failed for lot {lot_id} at event {i}"
                )
                return False
            prev_hash = h
        self._logger.info(f"Integrity check passed for lot {lot_id}")
        return True
