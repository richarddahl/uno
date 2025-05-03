# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
FastAPI app for Uno integrated example.
Exposes endpoints for InventoryItem aggregate.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from examples.app.persistence.inventory_item_repository_protocol import (
    InventoryItemRepository,
)
from examples.app.persistence.repository import InMemoryInventoryItemRepository
from examples.app.persistence.vendor_repository import InMemoryVendorRepository
from examples.app.persistence.vendor_repository_protocol import VendorRepository
from examples.app.services.inventory_item_service import InventoryItemService
from examples.app.services.vendor_service import VendorService
from uno.core.errors.definitions import DomainValidationError
from uno.core.errors.result import Failure
from uno.infrastructure.logging import LoggerService, LoggingConfig


def app_factory() -> FastAPI:
    app = FastAPI(title="Uno Example App", version="0.2.0")

    # --- Dependency Injection Setup ---
    from uno.infrastructure.di.container import ServiceCollection

    service_collection = ServiceCollection(
        auto_register=False
    )  # Explicitly disable auto-registration

    # Register LoggerService first
    logging_config = LoggingConfig()
    logger_service = LoggerService(logging_config)
    service_collection.add_instance(LoggerService, logger_service)

    # Register repositories with correct constructor args and bind to protocol
    service_collection.add_singleton(
        InventoryItemRepository,
        implementation=InMemoryInventoryItemRepository,
    )
    service_collection.add_singleton(
        VendorRepository,
        implementation=InMemoryVendorRepository,
    )
    # Register InventoryItemService and VendorService with protocol-based dependencies
    service_collection.add_singleton(
        InventoryItemService,
        implementation=InventoryItemService,
    )
    service_collection.add_singleton(
        VendorService,
        implementation=VendorService,
    )
    resolver = service_collection.build()

    # Resolve repositories via DI using protocol abstraction
    repo: InventoryItemRepository = resolver.resolve(InventoryItemRepository).value
    vendor_repo: VendorRepository = resolver.resolve(VendorRepository).value

    # Resolve VendorService via DI
    vendor_service: VendorService = resolver.resolve(VendorService).value

    # --- API Endpoints (rebind all endpoints here, using local repo variables) ---

    @app.post(
        "/inventory/",
        tags=["inventory"],
        response_model=dict,
        status_code=201,
    )
    def create_inventory_item(data: InventoryItemCreateDTO) -> dict:
        # Use DI to get the service
        inventory_item_service: InventoryItemService = resolver.resolve(
            InventoryItemService
        ).value
        result = inventory_item_service.create_inventory_item(
            aggregate_id=data.id, name=data.name, quantity=data.quantity
        )
        if isinstance(result, Failure):
            error = result.error
            if isinstance(error, DomainValidationError) and "already exists" in str(
                error
            ):
                raise HTTPException(status_code=409, detail=str(error))
            raise HTTPException(status_code=422, detail=str(error))
        item = result.unwrap()
        d = item.model_dump()
        if isinstance(d.get("quantity"), dict) and "value" in d["quantity"]:
            d["quantity"] = d["quantity"]["value"]
        return d

    @app.post("/vendors/", tags=["vendors"], response_model=dict, status_code=201)
    def create_vendor(data: VendorCreateDTO) -> dict:
        # Use the service layer for creation and error handling
        result = vendor_service.create_vendor(data.id, data.name, data.contact_email)
        if isinstance(result, Failure):
            raise HTTPException(status_code=400, detail=str(result.error))
        vendor = result.unwrap()
        vendor_repo.save(vendor)
        return vendor.model_dump()

    @app.get("/inventory/{aggregate_id}", tags=["inventory"], response_model=dict)
    def get_inventory_item(aggregate_id: str) -> dict:
        result = repo.get(aggregate_id)
        if isinstance(result, Failure):
            raise result.error
        item = result.unwrap()
        d = item.model_dump()
        if isinstance(d.get("quantity"), dict) and "value" in d["quantity"]:
            d["quantity"] = d["quantity"]["value"]
        return d

    @app.get("/vendors/{vendor_id}", tags=["vendors"], response_model=dict)
    def get_vendor(vendor_id: str) -> dict:
        result = vendor_repo.get(vendor_id)
        if isinstance(result, Failure):
            raise HTTPException(
                status_code=404, detail=f"Vendor not found: {vendor_id}"
            )
        vendor = result.value
        return vendor.model_dump()

    @app.put("/vendors/{vendor_id}", tags=["vendors"], response_model=dict)
    def update_vendor(vendor_id: str, data: VendorUpdateDTO) -> dict:
        """
        Update an existing vendor.
        """
        from examples.app.domain.value_objects import EmailAddress

        result = vendor_repo.get(vendor_id)
        if isinstance(result, Failure):
            raise HTTPException(status_code=404, detail=str(result.error))
        vendor = result.value
        vendor.name = data.name
        email_result = EmailAddress.from_value(data.contact_email)
        if isinstance(email_result, Failure):
            raise HTTPException(status_code=400, detail=str(email_result.error))
        vendor.contact_email = email_result.value
        vendor_repo.save(vendor)
        return vendor.model_dump()

    @app.get("/vendors/", tags=["vendors"], response_model=list[dict])
    def list_vendors() -> list[dict]:
        vendors = vendor_repo.all()
        result = []
        for v in vendors:
            result.append(v.model_dump())
        return result

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
