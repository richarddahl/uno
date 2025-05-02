# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Repository protocol for Vendor (Uno example app).
Defines the interface for all Vendor repository implementations.
"""
from typing import Protocol
from uno.core.errors.result import Success, Failure
from examples.app.domain.vendor import Vendor
from examples.app.api.errors import VendorNotFoundError

class VendorRepository(Protocol):
    def save(self, vendor: Vendor) -> None: ...
    def get(self, vendor_id: str) -> Success[Vendor, None] | Failure[None, VendorNotFoundError]:
        """
        Retrieve a vendor by id. Returns Success[Vendor, None] if found, Failure[None, VendorNotFoundError] if not found.
        """
        ...
    def all_ids(self) -> list[str]: ...
    def all(self) -> list[Vendor]: ...
