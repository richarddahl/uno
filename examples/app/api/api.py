# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
FastAPI app for Uno integrated example.
Exposes endpoints for InventoryItem aggregate.
"""
from fastapi import FastAPI, HTTPException
from uno.application.api_utils import as_canonical_json
from examples.app.persistence.repository import InMemoryInventoryItemRepository
from examples.app.persistence.vendor_repository import InMemoryVendorRepository
from examples.app.domain.vendor import Vendor
from examples.app.domain.inventory_item import InventoryItem
from examples.app.api.vendor_dtos import VendorDTO
from examples.app.api.dtos import InventoryItemDTO
from pydantic import BaseModel, Field

app = FastAPI(title="Uno Example App", version="0.2.0")

# In-memory repo singletons (demo only)
repo = InMemoryInventoryItemRepository()
vendor_repo = InMemoryVendorRepository()

@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}

# --- Vendor API ---
class VendorCreateDTO(BaseModel):
    id: str = Field(..., description="Vendor ID")
    name: str = Field(..., description="Vendor name")
    contact_email: str = Field(..., description="Contact email")

class VendorUpdateDTO(BaseModel):
    name: str = Field(..., description="Vendor name")
    contact_email: str = Field(..., description="Contact email")

@app.post("/vendors/", tags=["vendors"], response_model=VendorDTO, status_code=201)
def create_vendor(data: VendorCreateDTO) -> VendorDTO:
    if vendor_repo.get(data.id):
        raise HTTPException(status_code=409, detail=f"Vendor already exists: {data.id}")
    vendor = Vendor.create(vendor_id=data.id, name=data.name, contact_email=data.contact_email)
    vendor_repo.save(vendor)
    dto = VendorDTO(id=vendor.id, name=vendor.name, contact_email=vendor.contact_email)
    return as_canonical_json(dto)

@app.get("/vendors/{vendor_id}", tags=["vendors"], response_model=VendorDTO)
def get_vendor(vendor_id: str) -> VendorDTO:
    vendor = vendor_repo.get(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail=f"Vendor not found: {vendor_id}")
    dto = VendorDTO(id=vendor.id, name=vendor.name, contact_email=vendor.contact_email)
    return as_canonical_json(dto)

@app.put("/vendors/{vendor_id}", tags=["vendors"], response_model=VendorDTO)
def update_vendor(vendor_id: str, data: VendorUpdateDTO) -> VendorDTO:
    vendor = vendor_repo.get(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail=f"Vendor not found: {vendor_id}")
    vendor.update(name=data.name, contact_email=data.contact_email)
    vendor_repo.save(vendor)
    dto = VendorDTO(id=vendor.id, name=vendor.name, contact_email=vendor.contact_email)
    return as_canonical_json(dto)

@app.get("/vendors/", tags=["vendors"], response_model=list[VendorDTO])
def list_vendors() -> list[VendorDTO]:
    ids = vendor_repo.all_ids()
    result = []
    for vid in ids:
        vendor = vendor_repo.get(vid)
        if vendor:
            result.append(VendorDTO(id=vendor.id, name=vendor.name, contact_email=vendor.contact_email))
    return as_canonical_json(result)

@app.get("/inventory/{item_id}", tags=["inventory"], response_model=InventoryItemDTO)
def get_inventory_item(item_id: str) -> InventoryItemDTO:
    item = repo.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"InventoryItem not found: {item_id}")
    dto = InventoryItemDTO(id=item.id, name=item.name, quantity=item.quantity)
    return as_canonical_json(dto)

class InventoryItemCreateDTO(BaseModel):
    id: str = Field(..., description="Item ID")
    name: str = Field(..., description="Name of the inventory item")
    quantity: int = Field(..., description="Initial quantity")

@app.post("/inventory/", tags=["inventory"], response_model=InventoryItemDTO, status_code=201)
def create_inventory_item(data: InventoryItemCreateDTO) -> InventoryItemDTO:
    if repo.get(data.id):
        raise HTTPException(status_code=409, detail=f"InventoryItem already exists: {data.id}")
    item = InventoryItem.create(item_id=data.id, name=data.name, quantity=data.quantity)
    repo.save(item)
    dto = InventoryItemDTO(id=item.id, name=item.name, quantity=item.quantity)
    return as_canonical_json(dto)
