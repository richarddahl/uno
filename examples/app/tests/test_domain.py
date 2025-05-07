"""Tests for the example app domain models."""

import pytest
from typing import Any, Dict, Optional

from examples.app.domain.inventory.item import InventoryItem
from examples.app.domain.vendor.vendor import Vendor
from examples.app.domain.vendor.value_objects import EmailAddress
from uno.core.errors.result import Result, Success, Failure


class InventoryItemTests:
    """Test suite for InventoryItem aggregate."""

    def test_create_inventory_item(self) -> None:
        """Test creating an inventory item."""
        item = InventoryItem(id="item1", name="Test Item", measurement=10)
        assert item.id == "item1"
        assert item.name == "Test Item"
        assert item.measurement == 10

    def test_create_inventory_item_invalid_measurement(self) -> None:
        """Test creating an inventory item with invalid measurement."""
        with pytest.raises(ValueError):
            InventoryItem(id="item1", name="Test Item", measurement=-1)

    def test_update_inventory_item(self) -> None:
        """Test updating an inventory item."""
        item = InventoryItem(id="item1", name="Test Item", measurement=10)
        item.update_measurement(20)
        assert item.measurement == 20

    def test_update_inventory_item_invalid_measurement(self) -> None:
        """Test updating an inventory item with invalid measurement."""
        item = InventoryItem(id="item1", name="Test Item", measurement=10)
        with pytest.raises(ValueError):
            item.update_measurement(-1)

    def test_inventory_item_equality(self) -> None:
        """Test inventory item equality."""
        item1 = InventoryItem(id="item1", name="Test Item", measurement=10)
        item2 = InventoryItem(id="item1", name="Test Item", measurement=10)
        item3 = InventoryItem(id="item2", name="Test Item", measurement=10)
        assert item1 == item2
        assert item1 != item3

    def test_inventory_item_serialization(self) -> None:
        """Test inventory item serialization."""
        item = InventoryItem(id="item1", name="Test Item", measurement=10)
        data = item.model_dump()
        assert data["id"] == "item1"
        assert data["name"] == "Test Item"
        assert data["measurement"] == 10


class VendorTests:
    """Test suite for Vendor aggregate."""

    def test_create_vendor(self) -> None:
        email = EmailAddress(value="test@example.com")
        vendor = Vendor(id="vendor1", name="Test Vendor", email=email)
        assert vendor.id == "vendor1"
        assert vendor.name == "Test Vendor"
        assert vendor.email == email

    def test_create_vendor_invalid_email(self) -> None:
        """Test creating a vendor with invalid email."""
        with pytest.raises(ValueError):
            EmailAddress(value="invalid-email")

    def test_update_vendor(self) -> None:
        """Test updating a vendor."""
        email = EmailAddress(value="test@example.com")
        vendor = Vendor(id="vendor1", name="Test Vendor", email=email)
        new_email = EmailAddress(value="new@example.com")
        vendor.update_email(new_email)
        assert vendor.email == new_email

    def test_update_vendor_invalid_email(self) -> None:
        """Test updating a vendor with invalid email."""
        email = EmailAddress(value="test@example.com")
        vendor = Vendor(id="vendor1", name="Test Vendor", email=email)
        with pytest.raises(ValueError):
            vendor.update_email(EmailAddress(value="invalid-email"))

    def test_vendor_equality(self) -> None:
        """Test vendor equality."""
        email1 = EmailAddress(value="test@example.com")
        email2 = EmailAddress(value="test@example.com")
        vendor1 = Vendor(id="vendor1", name="Test Vendor", email=email1)
        vendor2 = Vendor(id="vendor1", name="Test Vendor", email=email2)
        assert vendor1 == vendor2

    def test_vendor_serialization(self) -> None:
        """Test vendor serialization."""
        email = EmailAddress(value="test@example.com")
        vendor = Vendor(id="vendor1", name="Test Vendor", email=email)
        data = vendor.model_dump()
        assert "id" in data
        assert "name" in data
        assert "email" in data
        assert "version" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "_events" in data
        assert "_version" in data
        assert "_created_at" in data
        assert "_updated_at" in data


class EmailAddressTests:
    """Test suite for EmailAddress value object."""

    def test_create_valid_email(self) -> None:
        """Test creating a valid email address."""
        email = EmailAddress(value="test@example.com")
        assert email.value == "test@example.com"

    def test_create_invalid_email(self) -> None:
        """Test creating an invalid email address."""
        with pytest.raises(ValueError):
            EmailAddress(value="invalid-email")

    def test_email_equality(self) -> None:
        """Test email address equality."""
        email1 = EmailAddress(value="test@example.com")
        email2 = EmailAddress(value="test@example.com")
        assert email1 == email2

    def test_email_serialization(self) -> None:
        """Test email address serialization."""
        email = EmailAddress(value="test@example.com")
        data = email.model_dump()
        assert "value" in data
        assert data["value"] == "test@example.com"