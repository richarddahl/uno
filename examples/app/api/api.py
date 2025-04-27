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
repo: InMemoryInventoryItemRepository = resolver.get(InMemoryInventoryItemRepository)
vendor_repo: InMemoryVendorRepository = resolver.get(InMemoryVendorRepository)
lot_repo: InMemoryInventoryLotRepository = resolver.get(InMemoryInventoryLotRepository)
order_repo: InMemoryOrderRepository = resolver.get(InMemoryOrderRepository)

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

from examples.app.api.errors import VendorNotFoundError, InventoryItemNotFoundError, InventoryLotNotFoundError, OrderNotFoundError
from uno.core.errors.result import Failure

@app.get("/vendors/{vendor_id}", tags=["vendors"], response_model=VendorDTO)
def get_vendor(vendor_id: str) -> VendorDTO:
    result = vendor_repo.get(vendor_id)
    if isinstance(result, Failure):
        raise result.error
    vendor = result.value
    dto = VendorDTO(id=vendor.id, name=vendor.name, contact_email=vendor.contact_email)
    return as_canonical_json(dto)

@app.get("/inventory/{item_id}", tags=["inventory"], response_model=InventoryItemDTO)
def get_inventory_item(item_id: str) -> InventoryItemDTO:
    result = repo.get(item_id)
    if isinstance(result, Failure):
        raise result.error
    item = result.value
    dto = InventoryItemDTO(id=item.id, name=item.name, quantity=item.quantity)
    return as_canonical_json(dto)

@app.get("/lots/{lot_id}", tags=["lots"], response_model=InventoryLotDTO)
def get_inventory_lot(lot_id: str) -> InventoryLotDTO:
    result = lot_repo.get(lot_id)
    if isinstance(result, Failure):
        raise result.error
    lot = result.value
    dto = InventoryLotDTO(id=lot.id, item_id=lot.item_id, vendor_id=lot.vendor_id, quantity=lot.quantity, purchase_price=lot.purchase_price, sale_price=lot.sale_price)
    return as_canonical_json(dto)

@app.get("/orders/{order_id}", tags=["orders"], response_model=OrderDTO)
def get_order(order_id: str) -> OrderDTO:
    result = order_repo.get(order_id)
    if isinstance(result, Failure):
        raise result.error
    order = result.value
    dto = OrderDTO(id=order.id, item_id=order.item_id, lot_id=order.lot_id, vendor_id=order.vendor_id, quantity=order.quantity, price=order.price, order_type=order.order_type, is_fulfilled=order.is_fulfilled, is_cancelled=order.is_cancelled)
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

# --- InventoryLot API ---
@app.post("/lots/", tags=["lots"], response_model=InventoryLotDTO, status_code=201)
def create_inventory_lot(data: InventoryLotCreateDTO) -> InventoryLotDTO:
    if lot_repo.get(data.id):
        raise HTTPException(status_code=409, detail=f"InventoryLot already exists: {data.id}")
    lot = InventoryLot.create(lot_id=data.id, item_id=data.item_id, quantity=data.quantity, vendor_id=data.vendor_id, purchase_price=data.purchase_price)
    lot_repo.save(lot)
    dto = InventoryLotDTO(id=lot.id, item_id=lot.item_id, vendor_id=lot.vendor_id, quantity=lot.quantity, purchase_price=lot.purchase_price, sale_price=lot.sale_price)
    return as_canonical_json(dto)

@app.get("/lots/{lot_id}", tags=["lots"], response_model=InventoryLotDTO)
def get_inventory_lot(lot_id: str) -> InventoryLotDTO:
    lot = lot_repo.get(lot_id)
    if not lot:
        raise HTTPException(status_code=404, detail=f"InventoryLot not found: {lot_id}")
    dto = InventoryLotDTO(id=lot.id, item_id=lot.item_id, vendor_id=lot.vendor_id, quantity=lot.quantity, purchase_price=lot.purchase_price, sale_price=lot.sale_price)
    return as_canonical_json(dto)

@app.patch("/lots/{lot_id}/adjust", tags=["lots"], response_model=InventoryLotDTO)
def adjust_inventory_lot(lot_id: str, data: InventoryLotAdjustDTO) -> InventoryLotDTO:
    lot = lot_repo.get(lot_id)
    if not lot:
        raise HTTPException(status_code=404, detail=f"InventoryLot not found: {lot_id}")
    lot.adjust_quantity(data.adjustment, reason=data.reason)
    lot_repo.save(lot)
    dto = InventoryLotDTO(id=lot.id, item_id=lot.item_id, vendor_id=lot.vendor_id, quantity=lot.quantity, purchase_price=lot.purchase_price, sale_price=lot.sale_price)
    return as_canonical_json(dto)

# --- Order API ---
@app.post("/orders/", tags=["orders"], response_model=OrderDTO, status_code=201)
def create_order(data: OrderCreateDTO) -> OrderDTO:
    if order_repo.get(data.id):
        raise HTTPException(status_code=409, detail=f"Order already exists: {data.id}")
    order = Order.create(order_id=data.id, item_id=data.item_id, lot_id=data.lot_id, vendor_id=data.vendor_id, quantity=data.quantity, price=data.price, order_type=data.order_type)
    order_repo.save(order)
    dto = OrderDTO(id=order.id, item_id=order.item_id, lot_id=order.lot_id, vendor_id=order.vendor_id, quantity=order.quantity, price=order.price, order_type=order.order_type, is_fulfilled=order.is_fulfilled, is_cancelled=order.is_cancelled)
    return as_canonical_json(dto)

@app.get("/orders/{order_id}", tags=["orders"], response_model=OrderDTO)
def get_order(order_id: str) -> OrderDTO:
    order = order_repo.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order not found: {order_id}")
    dto = OrderDTO(id=order.id, item_id=order.item_id, lot_id=order.lot_id, vendor_id=order.vendor_id, quantity=order.quantity, price=order.price, order_type=order.order_type, is_fulfilled=order.is_fulfilled, is_cancelled=order.is_cancelled)
    return as_canonical_json(dto)

@app.patch("/orders/{order_id}/fulfill", tags=["orders"], response_model=OrderDTO)
def fulfill_order(order_id: str, data: OrderFulfillDTO) -> OrderDTO:
    order = order_repo.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order not found: {order_id}")
    order.fulfill(data.fulfilled_quantity)
    order_repo.save(order)
    dto = OrderDTO(id=order.id, item_id=order.item_id, lot_id=order.lot_id, vendor_id=order.vendor_id, quantity=order.quantity, price=order.price, order_type=order.order_type, is_fulfilled=order.is_fulfilled, is_cancelled=order.is_cancelled)
    return as_canonical_json(dto)

@app.patch("/orders/{order_id}/cancel", tags=["orders"], response_model=OrderDTO)
def cancel_order(order_id: str, data: OrderCancelDTO) -> OrderDTO:
    order = order_repo.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order not found: {order_id}")
    order.cancel(data.reason)
    order_repo.save(order)
    dto = OrderDTO(id=order.id, item_id=order.item_id, lot_id=order.lot_id, vendor_id=order.vendor_id, quantity=order.quantity, price=order.price, order_type=order.order_type, is_fulfilled=order.is_fulfilled, is_cancelled=order.is_cancelled)
    return as_canonical_json(dto)

# --- Uno Error Handlers ---
from fastapi import Request
from fastapi.responses import JSONResponse
from examples.app.api.errors import ResourceNotFoundError

@app.exception_handler(ResourceNotFoundError)
async def resource_not_found_handler(request: Request, exc: ResourceNotFoundError):
    logger_service.error(f"{exc.resource_type} not found: {exc.resource_id}", exc_info=exc)
    return JSONResponse(status_code=404, content={"detail": str(exc)})
