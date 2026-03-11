"""Integration tests for API endpoints."""

import pytest
from datetime import datetime, timedelta

from src.models.ai_intelligence import IntelligenceItem, IntelligenceReport


class TestHealthEndpoint:
    """Test health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, async_client):
        """Test health endpoint returns correct structure."""
        response = await async_client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data


class TestDashboardEndpoints:
    """Test dashboard API endpoints."""

    @pytest.mark.asyncio
    async def test_get_dashboard_stats(self, async_client, db_session):
        """Test getting dashboard statistics."""
        # Create test data
        item = IntelligenceItem(
            source_type="arxiv",
            source_name="arXiv",
            external_id="test_001",
            title="Test Item",
            url="https://example.com",
            content_hash="hash123",
            category="research_paper",
            relevance_score=0.85,
            is_processed=True,
            is_read=False,
        )
        db_session.add(item)
        await db_session.commit()

        response = await async_client.get("/api/v1/dashboard/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total_items" in data
        assert "by_category" in data
        assert "by_source" in data

    @pytest.mark.asyncio
    async def test_list_intelligence_items(self, async_client, db_session):
        """Test listing intelligence items."""
        # Create test items
        for i in range(3):
            item = IntelligenceItem(
                source_type="github",
                source_name="GitHub",
                external_id=f"gh_{i}",
                title=f"Test Repo {i}",
                url=f"https://github.com/test/{i}",
                content_hash=f"hash_{i}",
                category="development_tool",
                relevance_score=0.7 + (i * 0.1),
                is_processed=True,
            )
            db_session.add(item)

        await db_session.commit()

        response = await async_client.get("/api/v1/dashboard/items")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data
        assert len(data["items"]) == 3

    @pytest.mark.asyncio
    async def test_list_items_with_filters(self, async_client, db_session):
        """Test listing items with filters."""
        # Create items with different categories
        categories = ["research_paper", "product", "development_tool"]
        for i, cat in enumerate(categories):
            item = IntelligenceItem(
                source_type="arxiv",
                source_name="arXiv",
                external_id=f"item_{i}",
                title=f"Item {i}",
                url=f"https://example.com/{i}",
                content_hash=f"hash_{i}",
                category=cat,
                relevance_score=0.8,
                is_processed=True,
            )
            db_session.add(item)

        await db_session.commit()

        # Test category filter
        response = await async_client.get("/api/v1/dashboard/items?category=research_paper")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["category"] == "research_paper"

        # Test relevance filter
        response = await async_client.get("/api/v1/dashboard/items?min_relevance=0.75")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3

    @pytest.mark.asyncio
    async def test_get_intelligence_item_detail(self, async_client, db_session):
        """Test getting single item details."""
        item = IntelligenceItem(
            id=1,
            source_type="arxiv",
            source_name="arXiv",
            external_id="arxiv_123",
            title="Test Paper",
            url="https://arxiv.org/abs/123",
            content_hash="hash_123",
            summary="Test summary",
            relevance_score=0.9,
            is_processed=True,
            is_read=False,
        )
        db_session.add(item)
        await db_session.commit()

        response = await async_client.get("/api/v1/dashboard/items/1")

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Paper"
        assert data["relevance_score"] == 0.9
        assert data["is_read"] is True  # Should be marked as read

    @pytest.mark.asyncio
    async def test_mark_item_read(self, async_client, db_session):
        """Test marking item as read."""
        item = IntelligenceItem(
            id=1,
            source_type="arxiv",
            source_name="arXiv",
            external_id="arxiv_123",
            title="Test Paper",
            url="https://arxiv.org/abs/123",
            content_hash="hash_123",
            is_read=False,
        )
        db_session.add(item)
        await db_session.commit()

        response = await async_client.post("/api/v1/dashboard/items/1/read")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify in database
        await db_session.refresh(item)
        assert item.is_read is True

    @pytest.mark.asyncio
    async def test_list_reports(self, async_client, db_session):
        """Test listing reports."""
        report = IntelligenceReport(
            report_type="daily",
            title="Daily Report - 2024-01-15",
            period_start=datetime.utcnow() - timedelta(days=1),
            period_end=datetime.utcnow(),
            summary="Test summary",
            highlights=[],
            category_breakdown={},
        )
        db_session.add(report)
        await db_session.commit()

        response = await async_client.get("/api/v1/dashboard/reports")

        assert response.status_code == 200
        data = response.json()
        assert len(data["reports"]) == 1
        assert data["reports"][0]["type"] == "daily"

    @pytest.mark.asyncio
    async def test_get_report_detail(self, async_client, db_session):
        """Test getting report details."""
        report = IntelligenceReport(
            id=1,
            report_type="daily",
            title="Daily Report",
            period_start=datetime.utcnow() - timedelta(days=1),
            period_end=datetime.utcnow(),
            summary="Test summary",
            highlights=[{"title": "Test", "relevance_score": 0.8}],
            category_breakdown={"research_paper": 5},
            trends_analysis="Test trends",
        )
        db_session.add(report)
        await db_session.commit()

        response = await async_client.get("/api/v1/dashboard/reports/1")

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "daily"
        assert "highlights" in data
        assert "category_breakdown" in data


class TestDocumentEndpoints:
    """Test document API endpoints."""

    @pytest.mark.asyncio
    async def test_list_documents(self, async_client):
        """Test listing documents."""
        response = await async_client.get("/api/v1/documents/list")

        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert "pagination" in data

    @pytest.mark.asyncio
    async def test_get_document_detail_not_found(self, async_client):
        """Test getting non-existent document."""
        response = await async_client.get("/api/v1/documents/nonexistent")

        assert response.status_code == 404


class TestOrganizationEndpoints:
    """Test organization API endpoints."""

    @pytest.mark.asyncio
    async def test_get_departments(self, async_client):
        """Test getting departments."""
        response = await async_client.get("/api/v1/organization/departments")

        assert response.status_code == 200
        data = response.json()
        assert "departments" in data

    @pytest.mark.asyncio
    async def test_get_employees(self, async_client):
        """Test getting employees."""
        response = await async_client.get("/api/v1/organization/employees")

        assert response.status_code == 200
        data = response.json()
        assert "employees" in data


class TestAPIErrorHandling:
    """Test API error handling."""

    @pytest.mark.asyncio
    async def test_404_error(self, async_client):
        """Test 404 error response."""
        response = await async_client.get("/api/v1/nonexistent")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_query_params(self, async_client):
        """Test invalid query parameter handling."""
        response = await async_client.get("/api/v1/dashboard/items?limit=invalid")

        # Should either convert to default or return 422
        assert response.status_code in [200, 422]
