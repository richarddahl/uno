# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Custom API error types for Uno example app, for idiomatic error handling and mapping to HTTP responses.
"""

from uno.core.errors.result import Result, Success, Failure


class ResourceNotFoundError(Exception):
    """Base class for all resource-not-found errors in the Uno API."""

    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(f"{resource_type} not found: {resource_id}")
        self.resource_type = resource_type
        self.resource_id = resource_id


class VendorNotFoundError(ResourceNotFoundError):
    def __init__(self, vendor_id: str):
        super().__init__("Vendor", vendor_id)


class InventoryItemNotFoundError(ResourceNotFoundError):
    def __init__(self, aggregate_id: str):
        super().__init__("InventoryItem", aggregate_id)


class InventoryLotNotFoundError(ResourceNotFoundError):
    def __init__(self, lot_id: str):
        super().__init__("InventoryLot", lot_id)


class OrderNotFoundError(ResourceNotFoundError):
    def __init__(self, order_id: str):
        super().__init__("Order", order_id)
