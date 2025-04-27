# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""DTOs for Order API."""
from pydantic import BaseModel, Field
from typing import Literal

class OrderDTO(BaseModel):
    id: str = Field(..., description="Order ID")
    item_id: str = Field(..., description="InventoryItem ID")
    lot_id: str = Field(..., description="InventoryLot ID")
    vendor_id: str = Field(..., description="Vendor ID")
    quantity: int = Field(..., description="Order quantity")
    price: float = Field(..., description="Order price")
    order_type: Literal["purchase", "sale"] = Field(..., description="Order type")
    is_fulfilled: bool = Field(..., description="Fulfillment status")
    is_cancelled: bool = Field(..., description="Cancellation status")

class OrderCreateDTO(BaseModel):
    id: str = Field(..., description="Order ID")
    item_id: str = Field(..., description="InventoryItem ID")
    lot_id: str = Field(..., description="InventoryLot ID")
    vendor_id: str = Field(..., description="Vendor ID")
    quantity: int = Field(..., description="Order quantity")
    price: float = Field(..., description="Order price")
    order_type: Literal["purchase", "sale"] = Field(..., description="Order type")

class OrderFulfillDTO(BaseModel):
    fulfilled_quantity: int = Field(..., description="Quantity fulfilled")

class OrderCancelDTO(BaseModel):
    reason: str | None = Field(None, description="Reason for cancellation")
