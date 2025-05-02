# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
FastAPI app for Uno integrated example.
Exposes endpoints for InventoryItem aggregate.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from examples.app.api.dtos import InventoryItemDTO
from examples.app.api.errors import (
    InventoryItemNotFoundError,
    InventoryLotNotFoundError,
    OrderNotFoundError,
    VendorNotFoundError,
)
from examples.app.api.inventory_lot_dtos import (
    InventoryLotAdjustDTO,
    InventoryLotCreateDTO,
    InventoryLotDTO,
)
from examples.app.api.order_dtos import (
    OrderCancelDTO,
    OrderCreateDTO,
    OrderDTO,
    OrderFulfillDTO,
)
from examples.app.api.vendor_dtos import VendorDTO
from examples.app.domain.inventory import InventoryItem
from examples.app.domain.inventory.lot import InventoryLot
from examples.app.domain.order import Order
from examples.app.domain.vendor import Vendor
from examples.app.persistence.inventory_item_repository_protocol import (
    InventoryItemRepository,
)
from examples.app.persistence.inventory_lot_repository import (
    InMemoryInventoryLotRepository,
)
from examples.app.persistence.order_repository import InMemoryOrderRepository
from examples.app.persistence.repository import InMemoryInventoryItemRepository
from examples.app.persistence.vendor_repository import InMemoryVendorRepository
from examples.app.persistence.vendor_repository_protocol import VendorRepository
from examples.app.services.inventory_item_service import InventoryItemService

from uno.core.errors.definitions import DomainValidationError
from uno.core.errors.result import Failure, Result, Success
from uno.core.logging import LoggerService, LoggingConfig


def app_factory() -> FastAPI:
    app = FastAPI(title="Uno Example App", version="0.2.0")

    # --- Dependency Injection Setup ---
    from uno.core.di.container import ServiceCollection

    service_collection = ServiceCollection(
        auto_register=False
    )  # Explicitly disable auto-registration
    logging_config = LoggingConfig()
    logger_service = LoggerService(logging_config)

    # Register LoggerService as a singleton instance only (correctly)
    service_collection.add_instance(LoggerService, logger_service)
    # Register repositories with correct constructor args and bind to protocol
    service_collection.add_singleton(
        InventoryItemRepository,
        implementation=InMemoryInventoryItemRepository,
        logger=logger_service,
    )
    service_collection.add_singleton(
        VendorRepository,
        implementation=InMemoryVendorRepository,
        logger=logger_service,
    )
    service_collection.add_singleton(
        InMemoryInventoryLotRepository,
        implementation=InMemoryInventoryLotRepository,
        logger=logger_service,
    )
    service_collection.add_singleton(
        InMemoryOrderRepository,
        implementation=InMemoryOrderRepository,
        logger=logger_service,
    )
    # Register InventoryItemService and VendorService with protocol-based dependencies
    service_collection.add_singleton(
        InventoryItemService,
        implementation=InventoryItemService,
    )
    from examples.app.services.vendor_service import VendorService

    service_collection.add_singleton(
        VendorService,
        implementation=VendorService,
    )
    resolver = service_collection.build()

    # Resolve repositories via DI using protocol abstraction
    repo: InventoryItemRepository = resolver.resolve(InventoryItemRepository).value
    vendor_repo: VendorRepository = resolver.resolve(VendorRepository).value
    lot_repo: InMemoryInventoryLotRepository = resolver.resolve(
        InMemoryInventoryLotRepository
    ).value
    order_repo: InMemoryOrderRepository = resolver.resolve(
        InMemoryOrderRepository
    ).value

    # Resolve VendorService via DI
    from examples.app.services.vendor_service import VendorService

    vendor_service: VendorService = resolver.resolve(VendorService).value

    # --- API Endpoints (rebind all endpoints here, using local repo variables) ---

    @app.post(
        "/inventory/",
        tags=["inventory"],
        response_model=InventoryItemDTO,
        status_code=201,
    )
    def create_inventory_item(data: InventoryItemCreateDTO) -> InventoryItemDTO:
        # Use DI to get the service
        inventory_item_service: InventoryItemService = resolver.resolve(
            InventoryItemService
        ).value
        result = inventory_item_service.create_inventory_item(
            item_id=data.id, name=data.name, quantity=data.quantity
        )
        if isinstance(result, Failure):
            error = result.error
            if isinstance(error, DomainValidationError) and "already exists" in str(
                error
            ):
                raise HTTPException(status_code=409, detail=str(error))
            raise HTTPException(status_code=422, detail=str(error))
        item = result.unwrap()
                # Extract primitive int value from Quantity value object for DTO
        qty = item.quantity.value.value if hasattr(item.quantity, 'value') and hasattr(item.quantity.value, 'value') else int(item.quantity)
        dto = InventoryItemDTO(id=item.id, name=item.name, quantity=qty)
        return dto

    @app.post("/vendors/", tags=["vendors"], response_model=VendorDTO, status_code=201)
    def create_vendor(data: VendorCreateDTO) -> VendorDTO:
        # Use the service layer for creation and error handling
        result = vendor_service.create_vendor(data.id, data.name, data.contact_email)
        if isinstance(result, Failure):
            raise HTTPException(status_code=400, detail=str(result.error))
        vendor = result.unwrap()
        vendor_repo.save(vendor)
        dto = VendorDTO(
            id=vendor.id,
            name=vendor.name,
            contact_email=vendor.contact_email.value
            if hasattr(vendor.contact_email, "value")
            else vendor.contact_email,
        )
        return dto

    @app.get(
        "/inventory/{item_id}", tags=["inventory"], response_model=InventoryItemDTO
    )
    def get_inventory_item(item_id: str) -> InventoryItemDTO:
        result = repo.get(item_id)
        if isinstance(result, Failure):
            raise result.error
        item = result.unwrap()
        # Extract primitive int value from Quantity value object for DTO
        qty = item.quantity.value.value if hasattr(item.quantity, 'value') and hasattr(item.quantity.value, 'value') else int(item.quantity)
        dto = InventoryItemDTO(id=item.id, name=item.name, quantity=qty)
        return dto

    @app.get("/vendors/{vendor_id}", tags=["vendors"], response_model=VendorDTO)
    def get_vendor(vendor_id: str) -> VendorDTO:
        result = vendor_repo.get(vendor_id)
        if isinstance(result, Failure):
            raise HTTPException(
                status_code=404, detail=f"Vendor not found: {vendor_id}"
            )
        vendor = result.value
        dto = VendorDTO(
            id=vendor.id,
            name=vendor.name,
            contact_email=vendor.contact_email.value
            if hasattr(vendor.contact_email, "value")
            else vendor.contact_email,
        )
        return dto

    @app.put("/vendors/{vendor_id}", tags=["vendors"], response_model=VendorDTO)
    def update_vendor(vendor_id: str, data: VendorUpdateDTO) -> VendorDTO:
        result = vendor_repo.get(vendor_id)
        if isinstance(result, Failure):
            raise HTTPException(
                status_code=404, detail=f"Vendor not found: {vendor_id}"
            )
        vendor = result.value
        vendor.name = data.name
        vendor.contact_email = data.contact_email
        vendor_repo.save(vendor)
        dto = VendorDTO(
            id=vendor.id,
            name=vendor.name,
            contact_email=vendor.contact_email.value
            if hasattr(vendor.contact_email, "value")
            else vendor.contact_email,
        )
        return dto

    @app.get("/vendors/", tags=["vendors"], response_model=list[VendorDTO])
    def list_vendors() -> list[VendorDTO]:
        vendors = vendor_repo.all()
        return [
            VendorDTO(
                id=v.id,
                name=v.name,
                contact_email=v.contact_email.value
                if hasattr(v.contact_email, "value")
                else v.contact_email,
            )
            for v in vendors
        ]

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


from examples.app.api.errors import (
    VendorNotFoundError,
    InventoryItemNotFoundError,
    InventoryLotNotFoundError,
    OrderNotFoundError,
)
from uno.core.errors.result import Failure
