# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
End-to-end test for InventoryItem API (Uno example app vertical slice)
"""

import pytest
from fastapi.testclient import TestClient
from examples.app.api.api import app_factory


@pytest.fixture
def client() -> TestClient:
    return TestClient(app_factory())


def test_inventory_item_lifecycle(client: TestClient) -> None:
    # Create a new inventory item
    item = {"id": "sku-123", "name": "Widget", "measurement": 10}
    resp = client.post("/inventory/", json=item)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == item["id"]
    assert data["name"] == item["name"]
    assert data["measurement"] == {"type": "count", "value": {"type": "count", "unit": "each", "value": 10.0}}
    # Fetch the same item
    resp2 = client.get(f"/inventory/{item['id']}")
    assert resp2.status_code == 200
    data2 = resp2.json()
    # Compare only relevant fields for Uno idiom
    assert data2["id"] == data["id"]
    assert data2["name"] == data["name"]
    assert data2["measurement"] == data["measurement"]
    # Try to create again (should conflict)
    resp3 = client.post("/inventory/", json=item)
    assert resp3.status_code == 409
    assert "already exists" in resp3.json()["detail"]
