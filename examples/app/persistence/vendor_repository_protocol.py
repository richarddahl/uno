# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Repository protocol for Vendor (Uno example app).
Defines the interface for all Vendor repository implementations.
"""

from typing import Protocol, runtime_checkable

from examples.app.domain.vendor import Vendor


@runtime_checkable
class VendorRepository(Protocol):
    def save(self, vendor: Vendor) -> None: ...
    def get(self, vendor_id: str) -> Vendor:
        """
        Retrieve a Vendor aggregate by replaying its event stream.

        Args:
            vendor_id: The unique ID of the Vendor.
        Returns:
            Vendor: The reconstructed Vendor, or raises VendorNotFoundError if not found.
        """
        ...

    def all_ids(self) -> list[str]: ...
    def all(self) -> list[Vendor]: ...
