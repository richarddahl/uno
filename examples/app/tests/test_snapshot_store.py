"""Tests for the example app snapshot store."""

import pytest
from typing import Any, Dict, Optional
from datetime import datetime

from examples.app.persistence.snapshot_store import InMemorySnapshotStore as SnapshotStore
from examples.app.domain.vendor.vendor import Vendor
from examples.app.domain.vendor.value_objects import EmailAddress
from uno.core.errors.result import Result, Success, Failure


class TestSnapshotStore:
    """Test suite for SnapshotStore."""

    def test_create_snapshot_store(self) -> None:
        """Test creating a snapshot store."""
        store = SnapshotStore()
        assert store is not None

    def test_snapshot_store_operations(self) -> None:
        """Test snapshot store operations."""
        store = SnapshotStore()
        email = EmailAddress(value="test@example.com")
        vendor = Vendor(
            id="vendor1",
            name="Test Vendor",
            email=email
        )
        
        # Test save snapshot
        result = store.save_snapshot("vendor1", vendor, 1)
        assert isinstance(result, Success)
        
        # Test get snapshot
        result = store.get_snapshot("vendor1", 1)
        assert isinstance(result, Success)
        snapshot = result.unwrap()
        assert snapshot.aggregate_id == "vendor1"
        assert snapshot.version == 1
        assert isinstance(snapshot.data, Vendor)
        assert snapshot.data.id == vendor.id
        assert snapshot.data.name == vendor.name
        assert snapshot.data.email.value == vendor.email.value
        
        # Test get latest snapshot
        result = store.get_latest_snapshot("vendor1")
        assert isinstance(result, Success)
        latest = result.unwrap()
        assert latest.aggregate_id == "vendor1"
        assert latest.version == 1
        
        # Test delete snapshot
        result = store.delete_snapshot("vendor1", 1)
        assert isinstance(result, Success)
        
        # Test get after delete
        result = store.get_snapshot("vendor1", 1)
        assert isinstance(result, Failure)

    def test_snapshot_versioning(self) -> None:
        """Test snapshot versioning."""
        store = SnapshotStore()
        email = EmailAddress(value="test@example.com")
        vendor = Vendor(
            id="vendor1",
            name="Test Vendor",
            email=email
        )
        
        # Save multiple versions
        store.save_snapshot("vendor1", vendor, 1)
        vendor.name = "Updated Vendor"
        store.save_snapshot("vendor1", vendor, 2)
        
        # Test get specific version
        result = store.get_snapshot("vendor1", 1)
        assert isinstance(result, Success)
        snapshot1 = result.unwrap()
        assert snapshot1.version == 1
        assert snapshot1.data.name == "Test Vendor"
        
        result = store.get_snapshot("vendor1", 2)
        assert isinstance(result, Success)
        snapshot2 = result.unwrap()
        assert snapshot2.version == 2
        assert snapshot2.data.name == "Updated Vendor"
        
        # Test get latest version
        result = store.get_latest_snapshot("vendor1")
        assert isinstance(result, Success)
        latest = result.unwrap()
        assert latest.version == 2
        assert latest.data.name == "Updated Vendor"

    def test_nonexistent_snapshot(self) -> None:
        """Test getting nonexistent snapshot."""
        store = SnapshotStore()
        
        # Test get nonexistent snapshot
        result = store.get_snapshot("nonexistent", 1)
        assert isinstance(result, Failure)
        
        # Test get latest nonexistent snapshot
        result = store.get_latest_snapshot("nonexistent")
        assert isinstance(result, Failure)
        
        # Test delete nonexistent snapshot
        result = store.delete_snapshot("nonexistent", 1)
        assert isinstance(result, Failure) 