"""Tests for the example app repository implementations."""

import pytest
from typing import Any, Dict, Optional
from datetime import datetime

from examples.app.persistence.repository import InMemoryInventoryItemRepository as Repository
from examples.app.persistence.vendor_repository import InMemoryVendorRepository as VendorRepository
from examples.app.persistence.inventory_lot_repository import InMemoryInventoryLotRepository as InventoryLotRepository
from examples.app.persistence.order_repository import InMemoryOrderRepository as OrderRepository
from examples.app.domain.vendor.vendor import Vendor
from examples.app.domain.vendor.value_objects import EmailAddress
from examples.app.domain.inventory.item import InventoryItem
from examples.app.domain.order.order import Order
from uno.core.errors.result import Result, Success, Failure


class TestRepository:
    """Test suite for base Repository class."""

    def test_create_repository(self) -> None:
        """Test creating a repository."""
        repo = Repository[Any]()
        assert repo is not None

    def test_repository_operations(self) -> None:
        """Test basic repository operations."""
        repo = Repository[Any]()
        item = {"id": "test1", "name": "Test Item"}
        
        # Test save
        result = repo.save(item)
        assert isinstance(result, Success)
        
        # Test get
        result = repo.get("test1")
        assert isinstance(result, Success)
        assert result.unwrap() == item
        
        # Test delete
        result = repo.delete("test1")
        assert isinstance(result, Success)
        
        # Test get after delete
        result = repo.get("test1")
        assert isinstance(result, Failure)


class TestVendorRepository:
    """Test suite for VendorRepository."""

    def test_create_vendor_repository(self) -> None:
        """Test creating a vendor repository."""
        repo = VendorRepository()
        assert repo is not None

    def test_vendor_repository_operations(self) -> None:
        """Test vendor repository operations."""
        repo = VendorRepository()
        vendor = Vendor(
            id="vendor1",
            name="Test Vendor",
            contact_email=EmailAddress("test@example.com")
        )
        
        # Test save
        result = repo.save(vendor)
        assert isinstance(result, Success)
        
        # Test get
        result = repo.get("vendor1")
        assert isinstance(result, Success)
        saved_vendor = result.unwrap()
        assert saved_vendor.id == vendor.id
        assert saved_vendor.name == vendor.name
        assert saved_vendor.contact_email.value == vendor.contact_email.value
        
        # Test delete
        result = repo.delete("vendor1")
        assert isinstance(result, Success)
        
        # Test get after delete
        result = repo.get("vendor1")
        assert isinstance(result, Failure)


class TestInventoryLotRepository:
    """Test suite for InventoryLotRepository."""

    def test_create_inventory_lot_repository(self) -> None:
        """Test creating an inventory lot repository."""
        repo = InventoryLotRepository()
        assert repo is not None

    def test_inventory_lot_repository_operations(self) -> None:
        """Test inventory lot repository operations."""
        repo = InventoryLotRepository()
        item = InventoryItem(
            id="item1",
            name="Test Item",
            measurement=10
        )
        
        # Test save
        result = repo.save(item)
        assert isinstance(result, Success)
        
        # Test get
        result = repo.get("item1")
        assert isinstance(result, Success)
        saved_item = result.unwrap()
        assert saved_item.id == item.id
        assert saved_item.name == item.name
        assert saved_item.measurement == item.measurement
        
        # Test delete
        result = repo.delete("item1")
        assert isinstance(result, Success)
        
        # Test get after delete
        result = repo.get("item1")
        assert isinstance(result, Failure)


class TestOrderRepository:
    """Test suite for OrderRepository."""

    def test_create_order_repository(self) -> None:
        """Test creating an order repository."""
        repo = OrderRepository()
        assert repo is not None

    def test_order_repository_operations(self) -> None:
        """Test order repository operations."""
        repo = OrderRepository()
        order = Order(
            id="order1",
            customer_id="customer1",
            items=[],
            status="pending",
            created_at=datetime.now()
        )
        
        # Test save
        result = repo.save(order)
        assert isinstance(result, Success)
        
        # Test get
        result = repo.get("order1")
        assert isinstance(result, Success)
        saved_order = result.unwrap()
        assert saved_order.id == order.id
        assert saved_order.customer_id == order.customer_id
        assert saved_order.status == order.status
        
        # Test delete
        result = repo.delete("order1")
        assert isinstance(result, Success)
        
        # Test get after delete
        result = repo.get("order1")
        assert isinstance(result, Failure) 