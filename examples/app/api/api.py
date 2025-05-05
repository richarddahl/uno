# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
FastAPI app for Uno integrated example.
Exposes endpoints for InventoryItem aggregate.
"""

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from examples.app.domain.vendor.value_objects import EmailAddress
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

# --- Dependency Injection Setup (module-level singletons) ---
from uno.infrastructure.di.container import ServiceCollection
from uno.infrastructure.logging import LoggerService, LoggingConfig

logging_config = LoggingConfig()
logger_service = LoggerService(logging_config)
vendor_repo = InMemoryVendorRepository(logger_service)
repo = InMemoryInventoryItemRepository(logger_service)

service_collection = ServiceCollection(auto_register=False)
service_collection.add_instance(LoggerService, logger_service)
service_collection.add_instance(VendorRepository, vendor_repo)
service_collection.add_instance(InMemoryVendorRepository, vendor_repo)
service_collection.add_instance(InventoryItemRepository, repo)
service_collection.add_instance(InMemoryInventoryItemRepository, repo)
service_collection.add_singleton(EmailAddress, implementation=EmailAddress)
service_collection.add_singleton(
    InventoryItemService, implementation=InventoryItemService
)
service_collection.add_singleton(
    VendorService,
    implementation=lambda: VendorService(repo=vendor_repo, logger=logger_service),
)
resolver = service_collection.build()


def app_factory() -> FastAPI:
    app = FastAPI(title="Uno Example App", version="0.2.0")

    # Use module-level singletons for all endpoints
    # (repo, vendor_repo, vendor_service, etc. are already resolved above)
    # ... (rest of the function remains unchanged)

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
            aggregate_id=data.id, name=data.name, measurement=data.measurement
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
        # Always return measurement as a dict with 'type', 'unit', and 'value' (for count measurements)
        return d

    @app.post("/vendors/", tags=["vendors"], response_model=dict, status_code=201)
    def create_vendor(data: VendorCreateDTO) -> dict:
        # Use the module-level singleton vendor_service
        vs: VendorService = resolver.resolve(VendorService).value
        result = vs.create_vendor(data.id, data.name, data.contact_email)
        if isinstance(result, Failure):
            raise HTTPException(status_code=400, detail=str(result.error))
        vendor = result.unwrap()
        return vendor.model_dump()

    @app.get("/inventory/{aggregate_id}", tags=["inventory"], response_model=dict)
    def get_inventory_item(aggregate_id: str) -> dict:
        result = repo.get(aggregate_id)
        if isinstance(result, Failure):
            raise result.error
        item = result.unwrap()
        d = item.model_dump()
        # Always return measurement as a dict with 'type', 'unit', and 'value' (for count measurements)
        return d

    @app.get("/vendors/{vendor_id}", tags=["vendors"], response_model=dict)
    def get_vendor(vendor_id: str) -> dict[str, Any]:
        vr: VendorRepository = resolver.resolve(VendorRepository).value
        result = vr.get(vendor_id)
        if isinstance(result, Failure):
            raise HTTPException(
                status_code=404, detail=f"Vendor not found: {vendor_id}"
            )
        vendor = result.value
        return vendor.model_dump()

    @app.put("/vendors/{vendor_id}", tags=["vendors"], response_model=dict)
    def update_vendor(vendor_id: str, data: VendorUpdateDTO) -> dict[str, Any]:
        """
        Update an existing vendor.
        """
        from examples.app.domain.vendor.value_objects import EmailAddress

        vr: VendorRepository = resolver.resolve(VendorRepository).value
        result = vr.get(vendor_id)
        if isinstance(result, Failure):
            raise HTTPException(status_code=404, detail=str(result.error))
        vendor = result.value
        vendor.name = data.name
        from pydantic import ValidationError

        try:
            vendor.contact_email = EmailAddress(value=data.contact_email)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        vr.save(vendor)
        return vendor.model_dump()

    @app.get("/vendors/", tags=["vendors"], response_model=list[dict])
    def list_vendors() -> list[dict[str, Any]]:
        vr: VendorRepository = resolver.resolve(VendorRepository).value
        vendors = vr.all()
        result = []
        for v in vendors:
            result.append(v.model_dump())
        return result

    # ...repeat for all other endpoints, rebinding vendor_repo, lot_repo, order_repo as needed...

    return app


class InventoryItemCreateDTO(BaseModel):
    id: str = Field(..., description="Inventory Item ID")
    name: str = Field(..., description="Inventory Item Name")
    measurement: int = Field(..., description="Initial Measurement")


class VendorCreateDTO(BaseModel):
    id: str = Field(..., description="Vendor ID")
    name: str = Field(..., description="Vendor name")
    contact_email: str = Field(..., description="Contact email")


class VendorUpdateDTO(BaseModel):
    name: str = Field(..., description="Vendor name")
    contact_email: str = Field(..., description="Contact email")
