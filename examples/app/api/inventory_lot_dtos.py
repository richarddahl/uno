# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""DTOs for InventoryLot API."""

from pydantic import BaseModel, Field


class InventoryLotDTO(BaseModel):
    id: str = Field(..., description="Lot ID")
    aggregate_id: str = Field(..., description="InventoryItem ID")
    vendor_id: str | None = Field(None, description="Vendor ID")
    quantity: int = Field(..., description="Quantity in lot")
    purchase_price: float | None = Field(
        None, description="Purchase price, if purchased"
    )
    sale_price: float | None = Field(None, description="Sale price, if sold")


class InventoryLotCreateDTO(BaseModel):
    id: str = Field(..., description="Lot ID")
    aggregate_id: str = Field(..., description="InventoryItem ID")
    vendor_id: str | None = Field(None, description="Vendor ID")
    quantity: int = Field(..., description="Quantity in lot")
    purchase_price: float | None = Field(
        None, description="Purchase price, if purchased"
    )


class InventoryLotAdjustDTO(BaseModel):
    adjustment: int = Field(..., description="Adjustment amount (+/-)")
    reason: str | None = Field(None, description="Reason for adjustment")
