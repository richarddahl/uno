"""Tests for the example app main entry point."""
from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient

from examples.app.api.api import app_factory


class TestMain:
    """Test suite for main application entry point."""

    @pytest_asyncio.fixture
    async def app(self) -> AsyncGenerator[FastAPI, None]:
        """Create a test app instance."""
        app = await app_factory()
        yield app

    @pytest.fixture
    def client(self, app: FastAPI) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_app_factory(self) -> None:
        """Test the app factory function."""
        app = await app_factory()
        assert app is not None
        assert isinstance(app, FastAPI)

    def test_app_routes(self, client: TestClient) -> None:
        """Test that all routes are registered."""
        # Test inventory routes
        response = client.get("/inventory/")
        assert response.status_code == 200
        
        response = client.post(
            "/inventory/",
            json={
                "id": "item1",
                "name": "Test Item",
                "measurement": 10
            }
        )
        assert response.status_code == 201
        
        response = client.get("/inventory/item1")
        assert response.status_code == 200
        
        # Test vendor routes
        response = client.get("/vendors/")
        assert response.status_code == 200
        
        response = client.post(
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

    def test_app_error_handling(self, client: TestClient) -> None:
        """Test application error handling."""
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

    def test_app_validation(self, client: TestClient) -> None:
        """Test request validation."""
        # Test missing required fields
        response = client.post(
            "/vendors/",
            json={
                "id": "vendor1",
                "name": "Test Vendor"
                # Missing contact_email
            }
        )
        assert response.status_code == 422

        # Test invalid field types
        response = client.post(
            "/inventory/",
            json={
                "id": "item1",
                "name": "Test Item",
                "measurement": "invalid"  # Should be number
            }
        )
        assert response.status_code == 422

    def test_app_response_format(self, client: TestClient) -> None:
        """Test response format consistency."""
        # Test successful response format
        response = client.get("/vendors/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Test error response format
        response = client.get("/vendors/nonexistent")
        assert response.status_code == 404
        error = response.json()
        assert "detail" in error 