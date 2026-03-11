"""Unit tests for R&D Health Metrics Service."""

import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.metrics.rnd_health import (
    RnDHealthMetricsService,
    RnDHealthMetrics,
)


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def metrics_service(mock_db_session):
    """Create a metrics service instance."""
    return RnDHealthMetricsService(mock_db_session)


class TestRnDHealthMetricsService:
    """Test R&D Health Metrics Service."""

    @pytest.mark.asyncio
    async def test_calculate_health_metrics_basic(self, metrics_service, mock_db_session):
        """Test basic health metrics calculation."""
        # Setup mock return values
        mock_db_session.execute.side_effect = [
            # _get_completed_tasks_count: 80 completed tasks
            AsyncMock(scalar=MagicMock(return_value=80)),
            # _get_total_tasks_count: 100 total tasks
            AsyncMock(scalar=MagicMock(return_value=100)),
            # _calculate_task_delay_rate: 10 overdue tasks out of 80 completed
            AsyncMock(scalar=MagicMock(return_value=10)),
            AsyncMock(scalar=MagicMock(return_value=80)),
            # _get_tech_debt_stats: 15 tech debt tasks out of 100
            AsyncMock(scalar=MagicMock(return_value=15)),
            AsyncMock(scalar=MagicMock(return_value=100)),
            # _calculate_single_point_dependencies
            AsyncMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[1]*30)))),
            AsyncMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[1]*100)))),
            # _calculate_r_and_d_protection_time: 5 urgent tasks
            AsyncMock(scalar=MagicMock(return_value=5)),
            AsyncMock(scalar=MagicMock(return_value=100)),
            # _get_overdue_tasks_count
            AsyncMock(scalar=MagicMock(return_value=12)),
            # _get_top_modules
            AsyncMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
        ]

        # Execute
        metrics = await metrics_service.calculate_health_metrics(
            start_date=date.today() - timedelta(days=30),
            end_date=date.today(),
        )

        # Verify
        assert isinstance(metrics, RnDHealthMetrics)
        assert 0 <= metrics.overall_health_score <= 1.0
        assert 0 <= metrics.module_maturity_index <= 1.0
        assert metrics.tasks_completed == 80
        assert metrics.tasks_total == 100
        assert metrics.tech_debt_tasks == 15
        assert metrics.overdue_tasks == 12

    @pytest.mark.asyncio
    async def test_get_trend_data(self, metrics_service, mock_db_session):
        """Test getting health trend data."""
        # Setup: mock calculate_health_metrics to return consistent values
        with patch.object(
            metrics_service,
            "calculate_health_metrics",
            return_value=RnDHealthMetrics(
                overall_health_score=0.75,
                module_maturity_index=0.8,
                ontime_completion_rate=0.85,
                tech_debt_concentration=0.15,
                task_delay_rate=0.12,
                single_point_dependency_risk=0.25,
                r_and_d_protection_time=0.55,
                tasks_completed=80,
                tasks_total=100,
                tech_debt_tasks=15,
                overdue_tasks=10,
                single_point_dependencies=25,
                top_modules=[],
            ),
        ):
            # Execute
            trend = await metrics_service.get_trend_data(days=30, interval_days=7)

            # Verify
            assert len(trend) > 0
            assert "date" in trend[0]
            assert "overall_score" in trend[0]
            assert trend[0]["overall_score"] == 0.75

    def test_calculate_ontime_completion_rate(self, metrics_service):
        """Test on-time completion rate calculation."""
        # Execute
        rate = metrics_service._calculate_ontime_completion_rate(80, 100)

        # Verify
        assert rate == 0.8

    def test_calculate_ontime_completion_rate_zero_total(self, metrics_service):
        """Test completion rate with zero total tasks."""
        # Execute
        rate = metrics_service._calculate_ontime_completion_rate(0, 0)

        # Verify
        assert rate == 0.0

    def test_calculate_module_maturity_index(self, metrics_service):
        """Test module maturity index calculation."""
        # Execute
        maturity = metrics_service._calculate_module_maturity_index(
            completion_rate=0.85,
            delay_rate=0.10,
        )

        # Verify
        expected = 0.85 * (1 - 0.10)
        assert maturity == expected
        assert 0 <= maturity <= 1.0

    def test_calculate_tech_debt_concentration(self, metrics_service):
        """Test tech debt concentration calculation."""
        # Execute
        concentration = metrics_service._calculate_tech_debt_concentration(
            tech_debt_count=15,
            total_count=100,
        )

        # Verify
        assert concentration == 0.15

    def test_calculate_tech_debt_concentration_zero_total(self, metrics_service):
        """Test tech debt concentration with zero total."""
        # Execute
        concentration = metrics_service._calculate_tech_debt_concentration(0, 0)

        # Verify
        assert concentration == 0.0

    def test_calculate_overall_health_score(self, metrics_service):
        """Test overall health score calculation."""
        # Execute
        score = metrics_service._calculate_overall_health_score(
            module_maturity_index=0.85,
            ontime_completion_rate=0.80,
            tech_debt_concentration=0.15,
            r_and_d_protection_time=0.60,
            single_point_dependency_risk=0.20,
        )

        # Verify: 0.30*0.85 + 0.25*0.80 + 0.20*(1-0.15) + 0.15*0.60 + 0.10*(1-0.20)
        expected = (
            0.30 * 0.85
            + 0.25 * 0.80
            + 0.20 * 0.85
            + 0.15 * 0.60
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
        assert metrics.tasks_completed == 0
        assert metrics.tasks_total == 0


class TestRnDHealthMetricsDataClass:
    """Test RnDHealthMetrics data class."""

    def test_create_metrics(self):
        """Test creating metrics instance."""
        # Execute
        metrics = RnDHealthMetrics(
            overall_health_score=0.75,
            module_maturity_index=0.80,
            ontime_completion_rate=0.85,
            tech_debt_concentration=0.15,
            task_delay_rate=0.12,
            single_point_dependency_risk=0.20,
            r_and_d_protection_time=0.60,
            tasks_completed=85,
            tasks_total=100,
            tech_debt_tasks=15,
            overdue_tasks=12,
            single_point_dependencies=20,
            top_modules=[
                {
                    "id": "proj-1",
                    "name": "Test Project",
                    "progress": 0.75,
                    "status": "in_progress",
                    "risk_level": "medium",
                }
            ],
        )

        # Verify
        assert metrics.overall_health_score == 0.75
        assert metrics.tasks_completed == 85
        assert len(metrics.top_modules) == 1
        assert metrics.top_modules[0]["name"] == "Test Project"
