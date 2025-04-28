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
from examples.app.persistence.inventory_lot_repository import InMemoryInventoryLotRepository
from examples.app.persistence.order_repository import InMemoryOrderRepository
from examples.app.domain.vendor import Vendor
from examples.app.domain.inventory_item import InventoryItem
from examples.app.domain.inventory_lot import InventoryLot
from examples.app.domain.order import Order
from examples.app.api.vendor_dtos import VendorDTO
from examples.app.api.dtos import InventoryItemDTO
from examples.app.api.inventory_lot_dtos import InventoryLotDTO, InventoryLotCreateDTO, InventoryLotAdjustDTO
from examples.app.api.order_dtos import OrderDTO, OrderCreateDTO, OrderFulfillDTO, OrderCancelDTO
from pydantic import BaseModel, Field

from uno.core.logging import LoggerService, LoggingConfig
from uno.core.di.container import ServiceCollection

def app_factory() -> FastAPI:
    app = FastAPI(title="Uno Example App", version="0.2.0")

    # --- Dependency Injection Setup ---
    service_collection = ServiceCollection()
    logging_config = LoggingConfig()
    logger_service = LoggerService(logging_config)

    # Register repositories with DI
    service_collection.add_singleton(LoggerService, instance=logger_service)
    service_collection.add_singleton(InMemoryInventoryItemRepository, implementation=InMemoryInventoryItemRepository, logger=logger_service)
    service_collection.add_singleton(InMemoryVendorRepository, implementation=InMemoryVendorRepository, logger=logger_service)
    service_collection.add_singleton(InMemoryInventoryLotRepository, implementation=InMemoryInventoryLotRepository, logger=logger_service)
    service_collection.add_singleton(InMemoryOrderRepository, implementation=InMemoryOrderRepository, logger=logger_service)

    # Build DI resolver
    resolver = service_collection.build()

    # Resolve repositories via DI (use .get() for raw instance, not monad)
    repo: InMemoryInventoryItemRepository = resolver.resolve(InMemoryInventoryItemRepository).value
    vendor_repo: InMemoryVendorRepository = resolver.resolve(InMemoryVendorRepository).value
    lot_repo: InMemoryInventoryLotRepository = resolver.resolve(InMemoryInventoryLotRepository).value
    order_repo: InMemoryOrderRepository = resolver.resolve(InMemoryOrderRepository).value

    # --- API Endpoints (rebind all endpoints here, using local repo variables) ---

    @app.post("/inventory/", tags=["inventory"], response_model=InventoryItemDTO, status_code=201)
    def create_inventory_item(data: InventoryItemCreateDTO) -> InventoryItemDTO:
        result = repo.get(data.id)
        if not isinstance(result, Failure):
            raise HTTPException(status_code=409, detail=f"InventoryItem already exists: {data.id}")
        item = InventoryItem.create(item_id=data.id, name=data.name, quantity=data.quantity)
        repo.save(item)
        dto = InventoryItemDTO(id=item.id, name=item.name, quantity=item.quantity)
        return as_canonical_json(dto)

    @app.post("/vendors/", tags=["vendors"], response_model=VendorDTO, status_code=201)
    def create_vendor(data: VendorCreateDTO) -> VendorDTO:
        result = vendor_repo.get(data.id)
        if not isinstance(result, Failure):
            raise HTTPException(status_code=409, detail=f"Vendor already exists: {data.id}")
        vendor = Vendor.create(vendor_id=data.id, name=data.name, contact_email=data.contact_email)
        vendor_repo.save(vendor)
        dto = VendorDTO(id=vendor.id, name=vendor.name, contact_email=vendor.contact_email)
        return as_canonical_json(dto)

    @app.get("/inventory/{item_id}", tags=["inventory"], response_model=InventoryItemDTO)
    def get_inventory_item(item_id: str) -> InventoryItemDTO:
        result = repo.get(item_id)
        if isinstance(result, Failure):
            raise result.error
        item = result
        dto = InventoryItemDTO(id=item.id, name=item.name, quantity=item.quantity)
        return as_canonical_json(dto)

    @app.get("/vendors/{vendor_id}", tags=["vendors"], response_model=VendorDTO)
    def get_vendor(vendor_id: str) -> VendorDTO:
        result = vendor_repo.get(vendor_id)
        if isinstance(result, Failure):
            raise HTTPException(status_code=404, detail=f"Vendor not found: {vendor_id}")
        vendor = result.value
        dto = VendorDTO(id=vendor.id, name=vendor.name, contact_email=vendor.contact_email)
        return as_canonical_json(dto)

    @app.put("/vendors/{vendor_id}", tags=["vendors"], response_model=VendorDTO)
    def update_vendor(vendor_id: str, data: VendorUpdateDTO) -> VendorDTO:
        result = vendor_repo.get(vendor_id)
        if isinstance(result, Failure):
            raise HTTPException(status_code=404, detail=f"Vendor not found: {vendor_id}")
        vendor = result.value
        vendor.name = data.name
        vendor.contact_email = data.contact_email
        vendor_repo.save(vendor)
        dto = VendorDTO(id=vendor.id, name=vendor.name, contact_email=vendor.contact_email)
        return as_canonical_json(dto)

    @app.get("/vendors/", tags=["vendors"], response_model=list[VendorDTO])
    def list_vendors() -> list[VendorDTO]:
        vendors = vendor_repo.all()
        return [VendorDTO(id=v.id, name=v.name, contact_email=v.contact_email) for v in vendors]

    # ...repeat for all other endpoints, rebinding vendor_repo, lot_repo, order_repo as needed...

    return app

class InventoryItemCreateDTO(BaseModel):
    id: str = Field(..., description="Inventory Item ID")
    name: str = Field(..., description="Inventory Item Name")
    quantity: int = Field(..., description="Initial Quantity")

class VendorCreateDTO(BaseModel):
    id: str = Field(..., description="Vendor ID")
    name: str = Field(..., description="Vendor name")
    contact_email: str = Field(..., description="Contact email")

class VendorUpdateDTO(BaseModel):
    name: str = Field(..., description="Vendor name")
    contact_email: str = Field(..., description="Contact email")

from examples.app.api.errors import VendorNotFoundError, InventoryItemNotFoundError, InventoryLotNotFoundError, OrderNotFoundError
from uno.core.errors.result import Failure


