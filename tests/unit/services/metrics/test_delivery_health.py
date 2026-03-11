"""Unit tests for Delivery Health Metrics Service."""

import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.metrics.delivery_health import (
    DeliveryHealthMetricsService,
    DeliveryHealthMetrics,
)


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def metrics_service(mock_db_session):
    """Create a metrics service instance."""
    return DeliveryHealthMetricsService(mock_db_session)


class TestDeliveryHealthMetricsService:
    """Test Delivery Health Metrics Service."""

    @pytest.mark.asyncio
    async def test_calculate_health_metrics_basic(
        self, metrics_service, mock_db_session
    ):
        """Test basic health metrics calculation."""
        # Setup mock return values
        mock_db_session.execute.side_effect = [
            # _get_project_on_time_stats: 8 on-time projects out of 10
            AsyncMock(scalar=MagicMock(return_value=8)),
            AsyncMock(scalar=MagicMock(return_value=10)),
            # _get_version_success_stats: 7 successful versions out of 10
            AsyncMock(scalar=MagicMock(return_value=7)),
            AsyncMock(scalar=MagicMock(return_value=10)),
            # _get_customer_issue_count: 3 customer issues
            AsyncMock(scalar=MagicMock(return_value=3)),
            # _calculate_rollback_risk: 1 failed/cancelled project out of 10
            AsyncMock(scalar=MagicMock(return_value=1)),
            AsyncMock(scalar=MagicMock(return_value=10)),
        ]

        # Execute
        metrics = await metrics_service.calculate_health_metrics(
            start_date=date.today() - timedelta(days=30),
            end_date=date.today(),
        )

        # Verify
        assert isinstance(metrics, DeliveryHealthMetrics)
        assert 0 <= metrics.overall_health_score <= 1.0
        assert metrics.delivery_on_time_rate == 0.8
        assert metrics.version_success_rate == 0.7
        assert metrics.customer_issue_rate == 0.3
        assert metrics.projects_on_time == 8
        assert metrics.projects_total == 10
        assert metrics.versions_success == 7
        assert metrics.versions_total == 10

    @pytest.mark.asyncio
    async def test_get_trend_data(self, metrics_service, mock_db_session):
        """Test getting health trend data."""
        # Setup: mock calculate_health_metrics to return consistent values
        with patch.object(
            metrics_service,
            "calculate_health_metrics",
            return_value=DeliveryHealthMetrics(
                overall_health_score=0.72,
                delivery_on_time_rate=0.80,
                version_success_rate=0.70,
                customer_issue_rate=0.30,
                implementation_rollback_risk=0.10,
                projects_on_time=8,
                projects_total=10,
                versions_success=7,
                versions_total=10,
            ),
        ):
            # Execute
            trend = await metrics_service.get_trend_data(days=30, interval_days=7)

            # Verify
            assert len(trend) > 0
            assert "date" in trend[0]
            assert "overall_score" in trend[0]
            assert trend[0]["overall_score"] == 0.72
            assert trend[0]["on_time_rate"] == 0.80

    def test_calculate_delivery_on_time_rate(self, metrics_service):
        """Test delivery on-time rate calculation."""
        # Execute
        rate = metrics_service._calculate_delivery_on_time_rate(8, 10)

        # Verify
        assert rate == 0.8

    def test_calculate_delivery_on_time_rate_zero_total(self, metrics_service):
        """Test on-time rate with zero total projects."""
        # Execute
        rate = metrics_service._calculate_delivery_on_time_rate(0, 0)

        # Verify
        assert rate == 0.0

    def test_calculate_version_success_rate(self, metrics_service):
        """Test version success rate calculation."""
        # Execute
        rate = metrics_service._calculate_version_success_rate(7, 10)

        # Verify
        assert rate == 0.7

    def test_calculate_customer_issue_rate(self, metrics_service):
        """Test customer issue rate calculation."""
        # Execute
        rate = metrics_service._calculate_customer_issue_rate(
            customer_issues=3,
            versions_total=10,
        )

        # Verify
        assert rate == 0.3

    def test_calculate_customer_issue_rate_zero_total(self, metrics_service):
        """Test customer issue rate with zero total."""
        # Execute
        rate = metrics_service._calculate_customer_issue_rate(0, 0)

        # Verify
        assert rate == 0.0

    def test_calculate_overall_health_score(self, metrics_service):
        """Test overall health score calculation."""
        # Execute
        score = metrics_service._calculate_overall_health_score(
            delivery_on_time_rate=0.80,
            version_success_rate=0.70,
            customer_issue_rate=0.30,
            rollback_risk=0.10,
        )

        # Verify: 0.40*0.80 + 0.30*0.70 + 0.20*(1-0.30) + 0.10*0.80
        expected = (
            0.40 * 0.80
            + 0.30 * 0.70
            + 0.20 * 0.70
            + 0.10 * 0.80
        )
        assert score == pytest.approx(expected, rel=0.01)
        assert 0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_calculate_health_metrics_empty_period(
        self, metrics_service, mock_db_session
    ):
        """Test metrics calculation with no data in period."""
        # Setup all queries to return 0
        mock_db_session.execute.return_value = AsyncMock(
            scalar=MagicMock(return_value=0)
        )

        # Execute
        metrics = await metrics_service.calculate_health_metrics(
            start_date=date.today() - timedelta(days=7),
            end_date=date.today(),
        )

        # Verify
        assert metrics.overall_health_score == 0.0
        assert metrics.projects_on_time == 0
        assert metrics.projects_total == 0

    def test_rollback_risk_calculation(self, metrics_service):
        """Test rollback risk calculation logic."""
        # Execute
        score = metrics_service._calculate_overall_health_score(
            delivery_on_time_rate=0.0,
            version_success_rate=0.0,
            customer_issue_rate=1.0,
            rollback_risk=1.0,
        )

        # Verify: minimum score should be 0
        assert score == 0.0

        # Test maximum score
        score_max = metrics_service._calculate_overall_health_score(
            delivery_on_time_rate=1.0,
            version_success_rate=1.0,
            customer_issue_rate=0.0,
            rollback_risk=0.0,
        )
        assert score_max == 1.0


class TestDeliveryHealthMetricsDataClass:
    """Test DeliveryHealthMetrics data class."""

    def test_create_metrics(self):
        """Test creating metrics instance."""
        # Execute
        metrics = DeliveryHealthMetrics(
            overall_health_score=0.72,
            delivery_on_time_rate=0.80,
            version_success_rate=0.70,
            customer_issue_rate=0.30,
            implementation_rollback_risk=0.10,
            projects_on_time=8,
            projects_total=10,
            versions_success=7,
            versions_total=10,
        )

        # Verify
        assert metrics.overall_health_score == 0.72
        assert metrics.projects_on_time == 8
        assert metrics.projects_total == 10
        assert metrics.versions_success == 7
        assert metrics.versions_total == 10
