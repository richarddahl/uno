"""Tests for the example app main entry point."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_asyncio import fixture

from examples.app.__main__ import create_app
from examples.app.api.api import app_factory


@pytest.fixture
async def test_app():
    return await create_app()


@pytest.fixture
async def test_client(test_app):
    return TestClient(test_app)


class TestMain:
    """Test suite for main application entry point."""

    async def test_create_app(self) -> None:
        """Test creating the application."""
        app = await create_app()
        assert app is not None

    async def test_app_factory(self) -> None:
        """Test the app factory function."""
        app = await app_factory()
        assert app is not None

    async def test_app_routes(self, test_client) -> None:
        """Test that all routes are registered."""
        # Test inventory routes
        response = test_client.get("/inventory/")
        assert response.status_code == 200
        
        response = test_client.post(
            "/inventory/",
            json={
                "id": "item1",
                "name": "Test Item",
                "measurement": 10
            }
        )
        assert response.status_code == 201
        
        response = test_client.get("/inventory/item1")
        assert response.status_code == 200
        
        # Test vendor routes
        response = test_client.get("/vendors/")
        assert response.status_code == 200
        
        response = test_client.post(
            "/vendors/",
            json={
                "id": "vendor1",
                "name": "Test Vendor",
                "contact_email": "test@example.com"
            }
        )
        assert response.status_code == 201
        
        response = client.get("/vendors/vendor1")
        assert response.status_code == 200

    async def test_app_error_handling(self) -> None:
        """Test application error handling."""
        app = await create_app()
        client = TestClient(app)
        
        # Test 404 for nonexistent route
        response = client.get("/nonexistent")
        assert response.status_code == 404
        
        # Test 400 for invalid request
        response = client.post(
            "/vendors/",
            json={
                "id": "vendor1",
                "name": "Test Vendor",
                "contact_email": "invalid-email"
            }
        )
        assert response.status_code == 400
        
        # Test 404 for nonexistent resource
        response = client.get("/vendors/nonexistent")
        assert response.status_code == 404