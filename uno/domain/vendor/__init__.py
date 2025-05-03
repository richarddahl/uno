"""
Vendor bounded context.

This module contains the public API for the Vendor domain, including:
- Aggregates: Vendor
- Events: VendorCreated, VendorUpdated
- Value Objects: EmailAddress (via uno.domain.value_objects)
"""

from .aggregates.vendor import Vendor
from .events import VendorCreated, VendorUpdated

__all__ = [
    "Vendor",
    "VendorCreated",
    "VendorUpdated",
]
