# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
FastAPI app for Uno integrated example.
Exposes endpoints for InventoryItem aggregate.
"""

from typing import Any

import time
from fastapi import FastAPI, HTTPException, Request, Response
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

# Import the new DI, error, config, and logging systems
from uno.di.container import Container
from uno.domain.di import register_domain_services
from uno.events.di import register_event_services
from uno.domain.errors import DomainValidationError
from uno.logging.protocols import LoggerProtocol
from uno.events.config import EventsConfig
from uno.domain.config import DomainConfig


async def app_factory() -> FastAPI:
    """
    Create and configure the FastAPI application with DI container.

    Returns:
        The configured FastAPI application
    """
    # Create and configure the DI container
    container = Container()

    # Register core services from uno framework
    await _register_core_services(container)

    # Register example app services
    await _register_app_services(container)

    # Create and configure the FastAPI app
    app = FastAPI(title="Uno Example App", version="0.3.0")

    # Store the container in the app state
    app.state.container = container

    # Add middleware for logging and error handling
    @app.middleware("http")
    async def logging_middleware(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        # Get the logger from the container
        logger = await container.resolve(LoggerProtocol)

        logger.info(
            "HTTP Request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            process_time_ms=round(process_time * 1000, 2),
        )
        return response

    # Add exception handler for domain errors
    @app.exception_handler(DomainValidationError)
    async def domain_error_handler(
        request: Request, exc: DomainValidationError
    ) -> Response:
        return Response(
            status_code=400,
            content={
                "error": "domain_validation_error",
                "message": str(exc),
                "details": exc.details if hasattr(exc, "details") else {},
            },
            media_type="application/json",
        )

    # --- API Endpoints ---
    @app.post(
        "/inventory/",
        tags=["inventory"],
        response_model=dict,
        status_code=201,
    )
    async def create_inventory_item(data: InventoryItemCreateDTO) -> dict:
        # Use DI to get the service from the container
        inventory_item_service = await container.resolve(InventoryItemService)

        try:
            item = await inventory_item_service.create_inventory_item(
                aggregate_id=data.id, name=data.name, measurement=data.measurement
            )
            return item.model_dump()
        except DomainValidationError as error:
            if "already exists" in str(error):
                raise HTTPException(status_code=409, detail=str(error))
            raise HTTPException(status_code=422, detail=str(error))
        except Exception as error:
            raise HTTPException(status_code=500, detail=str(error))

    @app.post("/vendors/", tags=["vendors"], response_model=dict, status_code=201)
    async def create_vendor(data: VendorCreateDTO) -> dict:
        # Use DI to get the service from the container
        vendor_service = await container.resolve(VendorService)

        try:
            vendor = await vendor_service.create_vendor(
                data.id, data.name, data.contact_email
            )
            return vendor.model_dump()
        except DomainValidationError as error:
            raise HTTPException(status_code=400, detail=str(error))
        except Exception as error:
            raise HTTPException(status_code=500, detail=str(error))

    @app.get("/inventory/{aggregate_id}", tags=["inventory"], response_model=dict)
    async def get_inventory_item(aggregate_id: str) -> dict:
        inventory_repo = await container.resolve(InventoryItemRepository)

        try:
            item = await inventory_repo.get(aggregate_id)
            if not item:
                raise HTTPException(
                    status_code=404, detail=f"Inventory item not found: {aggregate_id}"
                )
            return item.model_dump()
        except HTTPException:
            raise
        except Exception as error:
            raise HTTPException(status_code=500, detail=str(error))

    @app.get("/vendors/{vendor_id}", tags=["vendors"], response_model=dict)
    async def get_vendor(vendor_id: str) -> dict[str, Any]:
        vendor_repo = await container.resolve(VendorRepository)

        try:
            vendor = await vendor_repo.get(vendor_id)
            if not vendor:
                raise HTTPException(
                    status_code=404, detail=f"Vendor not found: {vendor_id}"
                )
            return vendor.model_dump()
        except HTTPException:
            raise
        except Exception as error:
            raise HTTPException(status_code=500, detail=str(error))

    @app.put("/vendors/{vendor_id}", tags=["vendors"], response_model=dict)
    async def update_vendor(vendor_id: str, data: VendorUpdateDTO) -> dict[str, Any]:
        """
        Update an existing vendor.
        """
        vendor_repo = await container.resolve(VendorRepository)

        try:
            vendor = await vendor_repo.get(vendor_id)
            if not vendor:
                raise HTTPException(
                    status_code=404, detail=f"Vendor not found: {vendor_id}"
                )

            vendor.name = data.name

            try:
                vendor.contact_email = EmailAddress(value=data.contact_email)
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

            await vendor_repo.save(vendor)
            return vendor.model_dump()
        except HTTPException:
            raise
        except Exception as error:
            raise HTTPException(status_code=500, detail=str(error))

    @app.get("/vendors/", tags=["vendors"], response_model=list[dict])
    async def list_vendors() -> list[dict[str, Any]]:
        vendor_repo = await container.resolve(VendorRepository)

        try:
            vendors = await vendor_repo.all()
            return [v.model_dump() for v in vendors]
        except Exception as error:
            raise HTTPException(status_code=500, detail=str(error))

    return app


async def _register_core_services(container: Container) -> None:
    """
    Register core services with the DI container.

    Args:
        container: The DI container
    """
    # Register domain and events services from uno framework
    await register_domain_services(container)
    await register_event_services(container)


async def _register_app_services(container: Container) -> None:
    """
    Register example app services with the DI container.

    Args:
        container: The DI container
    """
    # Get the logger from the container (registered by domain services)
    logger = await container.resolve(LoggerProtocol)

    # Register repositories as singletons
    vendor_repo = InMemoryVendorRepository(logger)
    inventory_repo = InMemoryInventoryItemRepository(logger)

    await container.register_singleton(VendorRepository, lambda _: vendor_repo)
    await container.register_singleton(
        InventoryItemRepository, lambda _: inventory_repo
    )

    # Register services with dependencies
    await container.register_singleton(
        VendorService, lambda c: VendorService(repo=vendor_repo, logger=logger)
    )

    await container.register_singleton(
        InventoryItemService,
        lambda c: InventoryItemService(repo=inventory_repo, logger=logger),
    )


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
