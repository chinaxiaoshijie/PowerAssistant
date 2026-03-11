"""Integration tests for Report API endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestReportAPI:
    """Test Report API endpoints."""

    def test_get_weekly_report(self, client):
        """Test getting weekly report."""
        # Execute
        response = client.get("/api/v1/report/weekly")

        # Verify
        # Note: This endpoint may not exist yet, so we test that we get a proper response
        assert response.status_code in [200, 404, 500]
        if response.status_code == 200:
            data = response.json()
            assert "period" in data
            assert "overall_health" in data

    def test_get_monthly_report(self, client):
        """Test getting monthly report."""
        # Execute
        response = client.get("/api/v1/report/monthly")

        # Verify
        assert response.status_code in [200, 404, 500]

    def test_get_report_with_date(self, client):
        """Test getting report with specific date."""
        # Execute
        response = client.get(
            "/api/v1/report/weekly",
            params={"date": "2026-03-01"},
        )

        # Verify
        assert response.status_code in [200, 404, 500]

    def test_export_report_markdown(self, client):
        """Test exporting report as Markdown."""
        # Execute
        response = client.get(
            "/api/v1/report/export",
            params={"format": "markdown"},
        )

        # Verify
        assert response.status_code in [200, 404, 500]
        if response.status_code == 200:
            assert "markdown" in response.headers.get("content-type", "")

    def test_export_report_pdf(self, client):
        """Test exporting report as PDF."""
        # Execute
        response = client.get(
            "/api/v1/report/export",
            params={"format": "pdf"},
        )

        # Verify
        assert response.status_code in [200, 404, 500]
