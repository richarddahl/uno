# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
In-memory event-sourced repository for Vendor aggregate (Uno example app).

Provides a simple, event-sourced repository for the Vendor aggregate using an in-memory event store.
"""

from typing import Any

from examples.app.api.errors import VendorNotFoundError
from examples.app.domain.vendor import Vendor, VendorCreated, VendorUpdated
from examples.app.domain.vendor.value_objects import EmailAddress
from uno.core.errors.result import Failure, Success
from uno.infrastructure.logging import LoggerService


class InMemoryVendorRepository:
    """
    Minimal in-memory event-sourced repository for Vendor aggregates.
    Stores and replays domain events for each Vendor by ID.
    """

    def __init__(self, logger: LoggerService) -> None:
        """Initialize the in-memory event store."""
        self._events: dict[str, list[Any]] = {}
        self._logger = logger
        self._logger.debug("InMemoryVendorRepository initialized.")

    def save(self, vendor: Vendor) -> Success[None, None] | Failure[None, Exception]:
        """
        Persist all new domain events for a Vendor aggregate.

        Args:
            vendor: The Vendor aggregate to save.
        """
        try:
            self._logger.info(f"Saving vendor: {vendor.id}")
            self._events.setdefault(vendor.id, []).extend(vendor._domain_events)
            vendor._domain_events.clear()
            self._logger.debug(
                f"Vendor {vendor.id} saved with {len(vendor._domain_events)} events."
            )
            return Success(None)
        except Exception as e:
            self._logger.error(f"Error saving vendor {vendor.id}: {e}")
            return Failure(e)

    def get(
        self, vendor_id: str
    ) -> Success[Vendor, None] | Failure[None, VendorNotFoundError]:
        """
        Retrieve a Vendor aggregate by replaying its event stream.

        Args:
            vendor_id: The unique ID of the Vendor.
        Returns:
            Success[Vendor] | Failure[VendorNotFoundError]: The reconstructed Vendor, or a VendorNotFoundError if not found.
        """
        events = self._events.get(vendor_id)
        if not events:
            self._logger.warning(f"Vendor not found: {vendor_id}")
            return Failure(VendorNotFoundError(vendor_id))
        vendor = None
        for event in events:
            if isinstance(event, VendorCreated):
                vendor = Vendor(
                    id=event.vendor_id,
                    name=event.name,
                    contact_email=EmailAddress(value=event.contact_email)
                    if isinstance(event.contact_email, str)
                    else event.contact_email,
                )
            elif isinstance(event, VendorUpdated) and vendor:
                vendor.name = event.name
                vendor.contact_email = (
                    EmailAddress(value=event.contact_email)
                    if isinstance(event.contact_email, str)
                    else event.contact_email
                )
        self._logger.debug(f"Fetched vendor: {vendor_id}")
        return Success(vendor)

    def all_ids(self) -> list[str]:
        """
        List all Vendor IDs present in the repository.
        Returns:
            list[str]: List of Vendor IDs.
        """
        ids = list(self._events.keys())
        self._logger.debug(f"Listing all vendor ids: {ids}")
        return ids

    def all(self) -> list[Vendor]:
        """
        Return all reconstructed Vendor aggregates in the repository.
        Returns:
            list[Vendor]: All vendors.
        """
        vendors: list[Vendor] = []
        for vendor_id in self.all_ids():
            result = self.get(vendor_id)
            if not isinstance(result, Failure):
                vendors.append(result.value)
        return vendors
