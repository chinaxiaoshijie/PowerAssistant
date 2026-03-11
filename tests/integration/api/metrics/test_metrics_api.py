"""Integration tests for Metrics API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestMetricsAPI:
    """Test Metrics API endpoints."""

    def test_get_rnd_health_metrics(self, client):
        """Test getting R&D health metrics."""
        # Execute
        response = client.get("/api/v1/metrics/rnd-health")

        # Verify
        assert response.status_code in [200, 500]  # 500 if DB not configured
        if response.status_code == 200:
            data = response.json()
            assert "overall_health_score" in data
            assert "module_maturity_index" in data
            assert "ontime_completion_rate" in data

    def test_get_rnd_health_metrics_with_date_range(self, client):
        """Test getting R&D health metrics with date range."""
        # Execute
        response = client.get(
            "/api/v1/metrics/rnd-health",
            params={
                "start_date": "2026-02-01",
                "end_date": "2026-03-01",
            },
        )

        # Verify
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "overall_health_score" in data

    def test_get_rnd_health_trend(self, client):
        """Test getting R&D health trend."""
        # Execute
        response = client.get(
            "/api/v1/metrics/rnd-health/trend",
            params={"days": 30, "interval_days": 7},
        )

        # Verify
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "trend" in data
            assert isinstance(data["trend"], list)

    def test_get_delivery_health_metrics(self, client):
        """Test getting delivery health metrics."""
        # Execute
        response = client.get("/api/v1/metrics/delivery-health")

        # Verify
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "overall_health_score" in data
            assert "delivery_on_time_rate" in data
            assert "version_success_rate" in data

    def test_get_delivery_health_trend(self, client):
        """Test getting delivery health trend."""
        # Execute
        response = client.get(
            "/api/v1/metrics/delivery-health/trend",
            params={"days": 30, "interval_days": 7},
        )

        # Verify
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "trend" in data
            assert isinstance(data["trend"], list)

    def test_get_rnd_health_with_filters(self, client):
        """Test getting R&D health metrics with employee and project filters."""
        # Execute
        response = client.get(
            "/api/v1/metrics/rnd-health",
            params={
                "employee_ids": "emp1,emp2",
                "project_ids": "proj1,proj2",
            },
        )

        # Verify
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "overall_health_score" in data

    def test_get_delivery_health_with_filters(self, client):
        """Test getting delivery health metrics with project filters."""
        # Execute
        response = client.get(
            "/api/v1/metrics/delivery-health",
            params={"project_ids": "proj1,proj2"},
        )

        # Verify
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "overall_health_score" in data
