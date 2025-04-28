# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
End-to-end tests for the Vendor API (Uno example app).
"""

import pytest
from fastapi.testclient import TestClient

from examples.app.api.api import app_factory


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app_factory())


def test_vendor_lifecycle(client: TestClient) -> None:
    # Create a new vendor
    vendor = {
        "id": "vendor-1",
        "name": "Acme Distilling",
        "contact_email": "info@acme.com",
    }
    resp = client.post("/vendors/", json=vendor)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["id"] == vendor["id"]
    assert data["name"] == vendor["name"]
    assert data["contact_email"] == vendor["contact_email"]

    # Fetch the same vendor
    resp2 = client.get(f"/vendors/{vendor['id']}")
    assert resp2.status_code == 200, resp2.text
    data2 = resp2.json()
    assert data2["id"] == vendor["id"]
    assert data2["name"] == vendor["name"]
    assert data2["contact_email"] == vendor["contact_email"]

    # Update the vendor
    update = {"name": "Acme Spirits", "contact_email": "hello@acme.com"}
    resp3 = client.put(f"/vendors/{vendor['id']}", json=update)
    assert resp3.status_code == 200, resp3.text
    data3 = resp3.json()
    assert data3["id"] == vendor["id"]
    assert data3["name"] == update["name"]
    assert data3["contact_email"] == update["contact_email"]

    # List all vendors
    resp4 = client.get("/vendors/")
    assert resp4.status_code == 200
    all_vendors = resp4.json()
    assert any(v["id"] == vendor["id"] for v in all_vendors)

    # Not found
    resp5 = client.get("/vendors/nonexistent")
    assert resp5.status_code == 404
