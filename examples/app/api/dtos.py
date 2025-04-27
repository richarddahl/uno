# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
DTOs for InventoryItem API (Uno example app)
Implements Uno canonical serialization contract.
"""

from pydantic import Field

from uno.core.application.dtos.dto import DTO


class InventoryItemDTO(DTO):
    id: str = Field(..., description="Item ID")
    name: str = Field(..., description="Name of the inventory item")
    quantity: int = Field(..., description="Current quantity")
