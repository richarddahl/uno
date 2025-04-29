# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Unit tests for InventoryItemService (Uno example app).
Covers all Result-based success and error paths, including validation and error context propagation.
"""
import pytest
from uno.core.errors.result import Success, Failure
from uno.core.errors.definitions import DomainValidationError
from uno.core.logging import LoggerService, LoggingConfig
from examples.app.domain.inventory_item import InventoryItem
from examples.app.services.inventory_item_service import InventoryItemService

class FakeInventoryItemRepository:
    def __init__(self):
        self._items = {}
    def get(self, item_id: str):
        item = self._items.get(item_id)
        if item:
            return Success(item)
        return Failure(Exception("not found"))
    def save(self, item: InventoryItem):
        self._items[item.id] = item
        return Success(item)

@pytest.fixture
def fake_logger() -> LoggerService:
    return LoggerService(LoggingConfig())

@pytest.fixture
def fake_repo() -> FakeInventoryItemRepository:
    return FakeInventoryItemRepository()

@pytest.fixture
def service(fake_repo: FakeInventoryItemRepository, fake_logger: LoggerService) -> InventoryItemService:
    return InventoryItemService(fake_repo, fake_logger)

def test_create_inventory_item_success(service: InventoryItemService) -> None:
    result = service.create_inventory_item("sku-1", "Widget", 5)
    assert isinstance(result, Success)
    item = result.value
    assert item.id == "sku-1"
    assert item.name == "Widget"
    assert item.quantity == 5

def test_create_inventory_item_duplicate(service: InventoryItemService) -> None:
    service.create_inventory_item("sku-1", "Widget", 5)
    result = service.create_inventory_item("sku-1", "Widget", 5)
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "already exists" in str(result.error)
    # Error context details
    assert getattr(result.error, "details", None)
    assert result.error.details["item_id"] == "sku-1"
    assert result.error.details["service"] == "InventoryItemService.create_inventory_item"

def test_create_inventory_item_invalid(service: InventoryItemService) -> None:
    result = service.create_inventory_item("sku-2", "", -1)
    assert isinstance(result, Failure)
    # Accept either DomainValidationError or other error, but check for context if present
    if isinstance(result.error, DomainValidationError):
        assert result.error.details["item_id"] == "sku-2"
        assert result.error.details["service"] == "InventoryItemService.create_inventory_item"
    else:
        assert "invalid" in str(result.error).lower()

def test_rename_inventory_item_success(service: InventoryItemService) -> None:
    service.create_inventory_item("sku-3", "Widget", 5)
    result = service.rename_inventory_item("sku-3", "Gadget")
    assert isinstance(result, Success)
    assert result.value.name == "Gadget"

def test_rename_inventory_item_not_found(service: InventoryItemService) -> None:
    result = service.rename_inventory_item("sku-404", "Gadget")
    assert isinstance(result, Failure)
    # Check error context details if present
    if isinstance(result.error, DomainValidationError):
        assert result.error.details["item_id"] == "sku-404"
        assert result.error.details["service"] == "InventoryItemService.rename_inventory_item"
    else:
        assert "not found" in str(result.error).lower()

def test_rename_inventory_item_invalid(service: InventoryItemService) -> None:
    service.create_inventory_item("sku-4", "Widget", 5)
    result = service.rename_inventory_item("sku-4", "")
    assert isinstance(result, Failure)
    # Accept either DomainValidationError or other error, but check for context if present
    if isinstance(result.error, DomainValidationError):
        assert result.error.details["item_id"] == "sku-4"
        assert result.error.details["service"] == "InventoryItemService.rename_inventory_item"
    else:
        assert "invalid" in str(result.error).lower()

def test_adjust_inventory_quantity_success(service) -> None:
    service.create_inventory_item("sku-5", "Widget", 5)
    result = service.adjust_inventory_quantity("sku-5", 3)
    assert isinstance(result, Success)
    assert result.value.quantity == 8

def test_adjust_inventory_quantity_negative(service) -> None:
    service.create_inventory_item("sku-6", "Widget", 5)
    result = service.adjust_inventory_quantity("sku-6", -3)
    assert isinstance(result, Success)
    assert result.value.quantity == 2

def test_adjust_inventory_quantity_invalid(service) -> None:
    service.create_inventory_item("sku-7", "Widget", 5)
    result = service.adjust_inventory_quantity("sku-7", -99)
    assert isinstance(result, Failure)
    # Accept either DomainValidationError or other error, but check for context if present
    if isinstance(result.error, DomainValidationError):
        assert result.error.details["item_id"] == "sku-7"
        assert result.error.details["service"] == "InventoryItemService.adjust_inventory_quantity"
    else:
        assert "invalid" in str(result.error).lower()

def test_adjust_inventory_quantity_not_found(service) -> None:
    result = service.adjust_inventory_quantity("sku-404", 1)
    assert isinstance(result, Failure)
    # Check error context details if present
    if isinstance(result.error, DomainValidationError):
        assert result.error.details["item_id"] == "sku-404"
        assert result.error.details["service"] == "InventoryItemService.adjust_inventory_quantity"
    else:
        assert "not found" in str(result.error).lower()
