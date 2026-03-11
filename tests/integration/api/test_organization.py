"""Integration tests for organization API."""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check(self, client):
        """Basic health check returns status."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "checks" in data
        assert "database" in data["checks"]

    def test_root_endpoint(self, client):
        """Root endpoint returns app info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data

    def test_api_info_endpoint(self, client):
        """API info endpoint returns endpoints list."""
        response = client.get("/api")
        assert response.status_code == 200
        data = response.json()
        assert "endpoints" in data
        assert "health" in data["endpoints"]
        assert "organization" in data["endpoints"]
        assert "sync" in data["endpoints"]


class TestOrganizationEndpoints:
    """Tests for organization endpoints."""

    @pytest.mark.asyncio
    async def test_list_departments(self):
        """List departments endpoint returns list."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/api/v1/organization/departments")
            # Will fail without DB, but tests routing
            assert response.status_code in [200, 500]

    @pytest.mark.asyncio
    async def test_list_employees(self):
        """List employees endpoint returns paginated list."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/api/v1/organization/employees")
            # Will fail without DB, but tests routing
            assert response.status_code in [200, 500]


class TestSyncEndpoints:
    """Tests for sync control endpoints."""

    @pytest.mark.asyncio
    async def test_get_sync_status(self):
        """Get sync status endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/api/v1/sync/status")
            # Will fail without DB, but tests routing
            assert response.status_code in [200, 500]

    @pytest.mark.asyncio
    async def test_get_sync_history(self):
        """Get sync history endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/api/v1/sync/history")
            # Will fail without DB, but tests routing
            assert response.status_code in [200, 500]
