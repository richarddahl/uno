"""Tests for the example app services."""

import pytest
from typing import Any, Dict, Optional

from examples.app.services.inventory_item_service import InventoryItemService
from examples.app.services.vendor_service import VendorService
from examples.app.persistence.inventory_item_repository_protocol import InventoryItemRepository
from examples.app.persistence.vendor_repository_protocol import VendorRepository
from uno.core.errors.result import Result, Success, Failure
from uno.infrastructure.logging import LoggerService, LoggingConfig


class MockInventoryItemRepository(InventoryItemRepository):
    """Mock inventory item repository for testing."""
    def __init__(self) -> None:
        self._items: Dict[str, Any] = {}

    def get(self, aggregate_id: str) -> Result[Any, Exception]:
        if aggregate_id not in self._items:
            return Failure(ValueError(f"Item not found: {aggregate_id}"))
        return Success(self._items[aggregate_id])

    def save(self, item: Any) -> Result[None, Exception]:
        self._items[item.id] = item
        return Success(None)

    def delete(self, aggregate_id: str) -> Result[None, Exception]:
        if aggregate_id in self._items:
            del self._items[aggregate_id]
            return Success(None)
        return Failure(ValueError(f"Item not found: {aggregate_id}"))


class MockVendorRepository(VendorRepository):
    """Mock vendor repository for testing."""
    def __init__(self) -> None:
        self._vendors: Dict[str, Any] = {}

    def get(self, vendor_id: str) -> Result[Any, Exception]:
        if vendor_id not in self._vendors:
            return Failure(ValueError(f"Vendor not found: {vendor_id}"))
        return Success(self._vendors[vendor_id])

    def save(self, vendor: Any) -> Result[None, Exception]:
        self._vendors[vendor.id] = vendor
        return Success(None)

    def delete(self, vendor_id: str) -> Result[None, Exception]:
        if vendor_id in self._vendors:
            del self._vendors[vendor_id]
            return Success(None)
        return Failure(ValueError(f"Vendor not found: {vendor_id}"))

    def all(self) -> list[Any]:
        return list(self._vendors.values())


class MockLoggerService(LoggerService):
    """Mock logger service for testing."""
    def __init__(self) -> None:
        self.logs: list[tuple[str, str]] = []

    def info(self, message: str) -> None:
        self.logs.append(("INFO", message))

    def error(self, message: str) -> None:
        self.logs.append(("ERROR", message))

    def warning(self, message: str) -> None:
        self.logs.append(("WARNING", message))

    def debug(self, message: str) -> None:
        self.logs.append(("DEBUG", message))


@pytest.fixture
def inventory_repo() -> MockInventoryItemRepository:
    """Create a mock inventory repository."""
    return MockInventoryItemRepository()


@pytest.fixture
def vendor_repo() -> MockVendorRepository:
    """Create a mock vendor repository."""
    return MockVendorRepository()


@pytest.fixture
def logger() -> MockLoggerService:
    """Create a mock logger service."""
    return MockLoggerService()


class InventoryItemServiceTests:
    """Test suite for InventoryItemService."""

    def test_create_inventory_item(self, inventory_repo: MockInventoryItemRepository, logger: MockLoggerService) -> None:
        """Test creating an inventory item."""
        service = InventoryItemService(repo=inventory_repo, logger=logger)
        result = service.create_inventory_item("item1", "Test Item", 10)
        assert isinstance(result, Success)
        item = result.unwrap()
        assert item.id == "item1"
        assert item.name == "Test Item"
        assert item.measurement == 10

    def test_create_duplicate_inventory_item(self, inventory_repo: MockInventoryItemRepository, logger: MockLoggerService) -> None:
        """Test creating a duplicate inventory item."""
        service = InventoryItemService(repo=inventory_repo, logger=logger)
        # Create first item
        service.create_inventory_item("item1", "Test Item", 10)
        # Try to create duplicate
        result = service.create_inventory_item("item1", "Test Item 2", 20)
        assert isinstance(result, Failure)

    def test_get_inventory_item(self, inventory_repo: MockInventoryItemRepository, logger: MockLoggerService) -> None:
        """Test getting an inventory item."""
        service = InventoryItemService(repo=inventory_repo, logger=logger)
        # Create item first
        service.create_inventory_item("item1", "Test Item", 10)
        # Get item
        result = inventory_repo.get("item1")
        assert isinstance(result, Success)
        item = result.unwrap()
        assert item.id == "item1"
        assert item.name == "Test Item"
        assert item.measurement == 10

    def test_get_nonexistent_inventory_item(self, inventory_repo: MockInventoryItemRepository, logger: MockLoggerService) -> None:
        """Test getting a nonexistent inventory item."""
        service = InventoryItemService(repo=inventory_repo, logger=logger)
        result = inventory_repo.get("nonexistent")
        assert isinstance(result, Failure)


class VendorServiceTests:
    """Test suite for VendorService."""

    def test_create_vendor(self, vendor_repo: MockVendorRepository, logger: MockLoggerService) -> None:
        """Test creating a vendor."""
        service = VendorService(repo=vendor_repo, logger=logger)
        result = service.create_vendor("vendor1", "Test Vendor", "test@example.com")
        assert isinstance(result, Success)
        vendor = result.unwrap()
        assert vendor.id == "vendor1"
        assert vendor.name == "Test Vendor"
        assert vendor.contact_email.value == "test@example.com"

    def test_create_vendor_invalid_email(self, vendor_repo: MockVendorRepository, logger: MockLoggerService) -> None:
        """Test creating a vendor with invalid email."""
        service = VendorService(repo=vendor_repo, logger=logger)
        result = service.create_vendor("vendor1", "Test Vendor", "invalid-email")
        assert isinstance(result, Failure)

    def test_get_vendor(self, vendor_repo: MockVendorRepository, logger: MockLoggerService) -> None:
        """Test getting a vendor."""
        service = VendorService(repo=vendor_repo, logger=logger)
        # Create vendor first
        service.create_vendor("vendor1", "Test Vendor", "test@example.com")
        # Get vendor
        result = vendor_repo.get("vendor1")
        assert isinstance(result, Success)
        vendor = result.unwrap()
        assert vendor.id == "vendor1"
        assert vendor.name == "Test Vendor"
        assert vendor.contact_email.value == "test@example.com"

    def test_get_nonexistent_vendor(self, vendor_repo: MockVendorRepository, logger: MockLoggerService) -> None:
        """Test getting a nonexistent vendor."""
        service = VendorService(repo=vendor_repo, logger=logger)
        result = vendor_repo.get("nonexistent")
        assert isinstance(result, Failure)

    def test_update_vendor(self, vendor_repo: MockVendorRepository, logger: MockLoggerService) -> None:
        """Test updating a vendor."""
        service = VendorService(repo=vendor_repo, logger=logger)
        # Create vendor first
        service.create_vendor("vendor1", "Test Vendor", "test@example.com")
        # Update vendor
        result = service.update_vendor("vendor1", "Updated Vendor", "updated@example.com")
        assert isinstance(result, Success)
        vendor = result.unwrap()
        assert vendor.id == "vendor1"
        assert vendor.name == "Updated Vendor"
        assert vendor.contact_email.value == "updated@example.com"

    def test_update_nonexistent_vendor(self, vendor_repo: MockVendorRepository, logger: MockLoggerService) -> None:
        """Test updating a nonexistent vendor."""
        service = VendorService(repo=vendor_repo, logger=logger)
        result = service.update_vendor("nonexistent", "Updated Vendor", "updated@example.com")
        assert isinstance(result, Failure)

    def test_list_vendors(self, vendor_repo: MockVendorRepository, logger: MockLoggerService) -> None:
        """Test listing vendors."""
        service = VendorService(repo=vendor_repo, logger=logger)
        # Create multiple vendors
        for i in range(3):
            service.create_vendor(
                f"vendor{i}",
                f"Test Vendor {i}",
                f"test{i}@example.com"
            )
        
        vendors = vendor_repo.all()
        assert len(vendors) == 3
        for i, vendor in enumerate(vendors):
            assert vendor.id == f"vendor{i}"
            assert vendor.name == f"Test Vendor {i}"
            assert vendor.contact_email.value == f"test{i}@example.com" 