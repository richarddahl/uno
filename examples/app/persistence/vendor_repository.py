# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
In-memory event-sourced repository for Vendor aggregate (Uno example app).

Provides a simple, event-sourced repository for the Vendor aggregate using an in-memory event store.
"""

from typing import Any

from examples.app.domain.vendor import Vendor, VendorCreated, VendorUpdated


class InMemoryVendorRepository:
    """
    Minimal in-memory event-sourced repository for Vendor aggregates.
    Stores and replays domain events for each Vendor by ID.
    """

    def __init__(self) -> None:
        """Initialize the in-memory event store."""
        self._events: dict[str, list[Any]] = {}

    def save(self, vendor: Vendor) -> None:
        """
        Persist all new domain events for a Vendor aggregate.

        Args:
            vendor: The Vendor aggregate to save.
        """
        self._events.setdefault(vendor.id, []).extend(vendor._domain_events)
        vendor._domain_events.clear()

    def get(self, vendor_id: str) -> Vendor | None:
        """
        Retrieve a Vendor aggregate by replaying its event stream.

        Args:
            vendor_id: The unique ID of the Vendor.
        Returns:
            Vendor | None: The reconstructed Vendor, or None if not found.
        """
        events = self._events.get(vendor_id)
        if not events:
            return None
        vendor = None
        for event in events:
            if isinstance(event, VendorCreated):
                vendor = Vendor(
                    id=event.vendor_id,
                    name=event.name,
                    contact_email=event.contact_email,
                )
            elif isinstance(event, VendorUpdated) and vendor:
                vendor.name = event.name
                vendor.contact_email = event.contact_email
        return vendor

    def all_ids(self) -> list[str]:
        """
        List all Vendor IDs present in the repository.
        Returns:
            list[str]: List of Vendor IDs.
        """
        return list(self._events.keys())
