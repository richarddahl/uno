"""Tests for the example app API endpoints."""

import pytest
from fastapi.testclient import TestClient
from typing import Any, Dict

from examples.app.api.api import app_factory
from examples.app.domain.vendor.value_objects import EmailAddress
from examples.app.persistence.inventory_item_repository_protocol import InventoryItemRepository
from examples.app.persistence.vendor_repository_protocol import VendorRepository


class MockInventoryItemRepository(InventoryItemRepository):
    """Mock inventory item repository for testing."""
    def __init__(self) -> None:
        self._items: Dict[str, Any] = {}

    def get(self, aggregate_id: str) -> Any:
        if aggregate_id not in self._items:
            return None
        return self._items[aggregate_id]

    def save(self, item: Any) -> None:
        self._items[item.id] = item

    def delete(self, aggregate_id: str) -> None:
        if aggregate_id in self._items:
            del self._items[aggregate_id]


class MockVendorRepository(VendorRepository):
    """Mock vendor repository for testing."""
    def __init__(self) -> None:
        self._vendors: Dict[str, Any] = {}

    def get(self, vendor_id: str) -> Any:
        if vendor_id not in self._vendors:
            return None
        return self._vendors[vendor_id]

    def save(self, vendor: Any) -> None:
        self._vendors[vendor.id] = vendor

    def delete(self, vendor_id: str) -> None:
        if vendor_id in self._vendors:
            del self._vendors[vendor_id]

    def all(self) -> list[Any]:
        return list(self._vendors.values())


@pytest.fixture
def client() -> TestClient:
    """Create a test client with mocked repositories."""
    app = app_factory()
    return TestClient(app)


class ApiTests:
    """Test suite for API endpoints."""

    def test_create_inventory_item(self, client: TestClient) -> None:
        """Test creating an inventory item."""
        response = client.post(
            "/inventory/",
            json={
                "id": "item1",
                "name": "Test Item",
                "measurement": 10
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "item1"
        assert data["name"] == "Test Item"
        assert data["measurement"] == 10

    def test_create_duplicate_inventory_item(self, client: TestClient) -> None:
        """Test creating a duplicate inventory item."""
        # Create first item
        client.post(
            "/inventory/",
            json={
                "id": "item1",
                "name": "Test Item",
                "measurement": 10
            }
        )
        
        # Try to create duplicate
        response = client.post(
            "/inventory/",
            json={
                "id": "item1",
                "name": "Test Item 2",
                "measurement": 20
            }
        )
        assert response.status_code == 409

    def test_get_inventory_item(self, client: TestClient) -> None:
        """Test getting an inventory item."""
        # Create item first
        client.post(
            "/inventory/",
            json={
                "id": "item1",
                "name": "Test Item",
                "measurement": 10
            }
        )
        
        # Get item
        response = client.get("/inventory/item1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "item1"
        assert data["name"] == "Test Item"
        assert data["measurement"] == 10

    def test_get_nonexistent_inventory_item(self, client: TestClient) -> None:
        """Test getting a nonexistent inventory item."""
        response = client.get("/inventory/nonexistent")
        assert response.status_code == 404

    def test_create_vendor(self, client: TestClient) -> None:
        """Test creating a vendor."""
        response = client.post(
            "/vendors/",
            json={
                "id": "vendor1",
                "name": "Test Vendor",
                "contact_email": "test@example.com"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "vendor1"
        assert data["name"] == "Test Vendor"
        assert data["contact_email"] == "test@example.com"

    def test_create_vendor_invalid_email(self, client: TestClient) -> None:
        """Test creating a vendor with invalid email."""
        response = client.post(
            "/vendors/",
            json={
                "id": "vendor1",
                "name": "Test Vendor",
                "contact_email": "invalid-email"
            }
        )
        assert response.status_code == 400

    def test_get_vendor(self, client: TestClient) -> None:
        """Test getting a vendor."""
        # Create vendor first
        client.post(
            "/vendors/",
            json={
                "id": "vendor1",
                "name": "Test Vendor",
                "contact_email": "test@example.com"
            }
        )
        
        # Get vendor
        response = client.get("/vendors/vendor1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "vendor1"
        assert data["name"] == "Test Vendor"
        assert data["contact_email"] == "test@example.com"

    def test_get_nonexistent_vendor(self, client: TestClient) -> None:
        """Test getting a nonexistent vendor."""
        response = client.get("/vendors/nonexistent")
        assert response.status_code == 404

    def test_update_vendor(self, client: TestClient) -> None:
        """Test updating a vendor."""
        # Create vendor first
        client.post(
            "/vendors/",
            json={
                "id": "vendor1",
                "name": "Test Vendor",
                "contact_email": "test@example.com"
            }
        )
        
        # Update vendor
        response = client.put(
            "/vendors/vendor1",
            json={
                "name": "Updated Vendor",
                "contact_email": "updated@example.com"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "vendor1"
        assert data["name"] == "Updated Vendor"
        assert data["contact_email"] == "updated@example.com"

    def test_update_nonexistent_vendor(self, client: TestClient) -> None:
        """Test updating a nonexistent vendor."""
        response = client.put(
            "/vendors/nonexistent",
            json={
                "name": "Updated Vendor",
                "contact_email": "updated@example.com"
            }
        )
        assert response.status_code == 404

    def test_list_vendors(self, client: TestClient) -> None:
        """Test listing vendors."""
        # Create multiple vendors
        vendors = [
            {
                "id": f"vendor{i}",
                "name": f"Test Vendor {i}",
                "contact_email": f"test{i}@example.com"
            }
            for i in range(3)
        ]
        
        for vendor in vendors:
            client.post("/vendors/", json=vendor)
        
        # List vendors
        response = client.get("/vendors/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        for vendor in data:
            assert vendor["id"] in [v["id"] for v in vendors]
            assert vendor["name"] in [v["name"] for v in vendors]
            assert vendor["contact_email"] in [v["contact_email"] for v in vendors] 