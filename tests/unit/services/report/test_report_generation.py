"""Unit tests for Report Generation Service."""

import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.report.report_generation import (
    ReportGenerationService,
    WeeklyReport,
)
from src.services.ai_engine import AIEngineService
from src.services.metrics.rnd_health import RnDHealthMetrics
from src.services.metrics.delivery_health import DeliveryHealthMetrics


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def mock_ai_service():
    """Create a mock AI service."""
    service = AsyncMock(spec=AIEngineService)
    service.generate_text = AsyncMock(return_value="- 建议优化流程")
    return service


@pytest.fixture
def report_service(mock_db_session, mock_ai_service):
    """Create a report service instance with AI."""
    return ReportGenerationService(mock_db_session, mock_ai_service)


@pytest.fixture
def report_service_no_ai(mock_db_session):
    """Create a report service instance without AI."""
    return ReportGenerationService(mock_db_session)


class TestWeeklyReportDataClass:
    """Test WeeklyReport data class."""

    def test_create_weekly_report(self):
        """Test creating a weekly report instance."""
        # Execute
        report = WeeklyReport(
            period_start=date(2026, 2, 24),
            period_end=date(2026, 3, 2),
            overall_health=0.75,
            key_metrics={
                "研发健康度": "75%",
                "任务准时完成率": "85%",
            },
            achievements=["任务完成率高"],
            challenges=["技术债较多"],
            recommendations=["优化流程"],
            highlights=[{"title": "AI进展", "description": "大模型突破"}],
            tasks_completed=50,
            tasks_in_progress=20,
            projects_on_track=5,
            projects_at_risk=2,
        )

        # Verify
        assert report.period_start == date(2026, 2, 24)
        assert report.period_end == date(2026, 3, 2)
        assert report.overall_health == 0.75
        assert report.tasks_completed == 50
        assert report.tasks_in_progress == 20
        assert len(report.achievements) == 1

    def test_to_dict(self):
        """Test converting report to dictionary."""
        # Setup
        report = WeeklyReport(
            period_start=date(2026, 2, 24),
            period_end=date(2026, 3, 2),
            overall_health=0.75,
            key_metrics={"研发健康度": "75%"},
            achievements=["成就1"],
            challenges=["挑战1"],
            recommendations=["建议1"],
            highlights=[],
            tasks_completed=50,
            tasks_in_progress=20,
            projects_on_track=5,
            projects_at_risk=2,
        )

        # Execute
        data = report.to_dict()

        # Verify
        assert data["period"]["start"] == "2026-02-24"
        assert data["period"]["end"] == "2026-03-02"
        assert data["overall_health"] == 0.75
        assert data["summary"]["tasks_completed"] == 50
        assert data["achievements"] == ["成就1"]

    def test_to_markdown(self):
        """Test converting report to Markdown."""
        # Setup
        report = WeeklyReport(
            period_start=date(2026, 2, 24),
            period_end=date(2026, 3, 2),
            overall_health=0.75,
            key_metrics={"研发健康度": "75%"},
            achievements=["成就1"],
            challenges=["挑战1"],
            recommendations=["建议1"],
            highlights=[],
            tasks_completed=50,
            tasks_in_progress=20,
            projects_on_track=5,
            projects_at_risk=2,
        )

        # Execute
        markdown = report.to_markdown()

        # Verify
        assert "# 周报" in markdown
        assert "75%" in markdown
        assert "成就1" in markdown
        assert "挑战1" in markdown
        assert "建议1" in markdown


class TestReportGenerationService:
    """Test Report Generation Service."""

    @pytest.mark.asyncio
    async def test_generate_weekly_report_with_ai(
        self, report_service, mock_db_session
    ):
        """Test generating weekly report with AI service."""
        # Setup mock metrics
        rnd_metrics = RnDHealthMetrics(
            overall_health_score=0.75,
            module_maturity_index=0.80,
            ontime_completion_rate=0.85,
            tech_debt_concentration=0.15,
            task_delay_rate=0.12,
            single_point_dependency_risk=0.25,
            r_and_d_protection_time=0.60,
            tasks_completed=80,
            tasks_total=100,
            tech_debt_tasks=15,
            overdue_tasks=12,
            single_point_dependencies=25,
            top_modules=[],
        )

        delivery_metrics = DeliveryHealthMetrics(
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

        # Mock the metrics services
        with patch(
            "src.services.report.report_generation.RnDHealthMetricsService"
        ) as mock_rnd_service_cls, patch(
            "src.services.report.report_generation.DeliveryHealthMetricsService"
        ) as mock_delivery_service_cls:
            mock_rnd_service = AsyncMock()
            mock_rnd_service.calculate_health_metrics.return_value = rnd_metrics
            mock_rnd_service_cls.return_value = mock_rnd_service

            mock_delivery_service = AsyncMock()
            mock_delivery_service.calculate_health_metrics.return_value = delivery_metrics
            mock_delivery_service_cls.return_value = mock_delivery_service

            # Mock highlights query
            mock_db_session.execute.return_value = AsyncMock(
                scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
            )

            # Execute
            report = await report_service.generate_weekly_report(week_offset=-1)

            # Verify
            assert isinstance(report, WeeklyReport)
            assert report.overall_health == 0.75
            assert report.tasks_completed == 80
            assert len(report.recommendations) > 0

    @pytest.mark.asyncio
    async def test_generate_weekly_report_without_ai(
        self, report_service_no_ai, mock_db_session
    ):
        """Test generating weekly report without AI service (rule-based)."""
        # Setup mock metrics
        rnd_metrics = RnDHealthMetrics(
            overall_health_score=0.75,
            module_maturity_index=0.80,
            ontime_completion_rate=0.85,
            tech_debt_concentration=0.25,
            task_delay_rate=0.12,
            single_point_dependency_risk=0.35,
            r_and_d_protection_time=0.45,
            tasks_completed=80,
            tasks_total=100,
            tech_debt_tasks=25,
            overdue_tasks=12,
            single_point_dependencies=35,
            top_modules=[],
        )

        delivery_metrics = DeliveryHealthMetrics(
            overall_health_score=0.72,
            delivery_on_time_rate=0.80,
            version_success_rate=0.70,
            customer_issue_rate=0.12,
            implementation_rollback_risk=0.18,
            projects_on_time=8,
            projects_total=10,
            versions_success=7,
            versions_total=10,
        )

        # Mock the metrics services
        with patch(
            "src.services.report.report_generation.RnDHealthMetricsService"
        ) as mock_rnd_service_cls, patch(
            "src.services.report.report_generation.DeliveryHealthMetricsService"
        ) as mock_delivery_service_cls:
            mock_rnd_service = AsyncMock()
            mock_rnd_service.calculate_health_metrics.return_value = rnd_metrics
            mock_rnd_service_cls.return_value = mock_rnd_service

            mock_delivery_service = AsyncMock()
            mock_delivery_service.calculate_health_metrics.return_value = delivery_metrics
            mock_delivery_service_cls.return_value = mock_delivery_service

            # Mock highlights query
            mock_db_session.execute.return_value = AsyncMock(
                scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
            )

            # Execute
            report = await report_service_no_ai.generate_weekly_report(week_offset=-1)

            # Verify
            assert isinstance(report, WeeklyReport)
            assert len(report.recommendations) > 0
            # Should have rule-based recommendations based on metrics
            assert any("技术债" in r for r in report.recommendations)
            assert any("单点依赖" in r for r in report.recommendations)

    def test_generate_rule_based_recommendations(self, report_service_no_ai):
        """Test rule-based recommendation generation."""
        # Setup metrics with issues
        rnd_metrics = RnDHealthMetrics(
            overall_health_score=0.60,
            module_maturity_index=0.65,
            ontime_completion_rate=0.70,
            tech_debt_concentration=0.30,
            task_delay_rate=0.30,
            single_point_dependency_risk=0.45,
            r_and_d_protection_time=0.40,
            tasks_completed=70,
            tasks_total=100,
            tech_debt_tasks=30,
            overdue_tasks=21,
            single_point_dependencies=45,
            top_modules=[],
        )

        delivery_metrics = DeliveryHealthMetrics(
            overall_health_score=0.65,
            delivery_on_time_rate=0.75,
            version_success_rate=0.65,
            customer_issue_rate=0.18,
            implementation_rollback_risk=0.20,
            projects_on_time=7,
            projects_total=10,
            versions_success=6,
            versions_total=10,
        )

        # Execute
        recommendations = report_service_no_ai._generate_rule_based_recommendations(
            rnd_metrics, delivery_metrics
        )

        # Verify
        assert len(recommendations) > 0
        assert len(recommendations) <= 5  # Should be limited to 5
        assert any("技术债" in r for r in recommendations)
        assert any("单点依赖" in r for r in recommendations)
        assert any("客户问题" in r for r in recommendations)
        assert any("实施风险" in r for r in recommendations)

    def test_compile_achievements(self, report_service_no_ai):
        """Test compiling achievements from metrics."""
        # Setup good metrics
        rnd_metrics = RnDHealthMetrics(
            overall_health_score=0.85,
            module_maturity_index=0.88,
            ontime_completion_rate=0.90,
            tech_debt_concentration=0.08,
            task_delay_rate=0.10,
            single_point_dependency_risk=0.20,
            r_and_d_protection_time=0.65,
            tasks_completed=90,
            tasks_total=100,
            tech_debt_tasks=8,
            overdue_tasks=10,
            single_point_dependencies=20,
            top_modules=[],
        )

        delivery_metrics = DeliveryHealthMetrics(
            overall_health_score=0.88,
            delivery_on_time_rate=0.92,
            version_success_rate=0.95,
            customer_issue_rate=0.05,
            implementation_rollback_risk=0.05,
            projects_on_time=9,
            projects_total=10,
            versions_success=9,
            versions_total=10,
        )

        # Execute
        achievements = report_service_no_ai._compile_achievements(
            rnd_metrics, delivery_metrics, date.today(), date.today()
        )

        # Verify
        assert len(achievements) >= 3  # Should have multiple achievements
        assert any("准时完成率" in a for a in achievements)
        assert any("健康度" in a for a in achievements)
        assert any("版本成功率" in a for a in achievements)

    def test_compile_challenges(self, report_service_no_ai):
        """Test compiling challenges from metrics."""
        # Setup poor metrics
        rnd_metrics = RnDHealthMetrics(
            overall_health_score=0.50,
            module_maturity_index=0.55,
            ontime_completion_rate=0.50,
            tech_debt_concentration=0.35,
            task_delay_rate=0.40,
            single_point_dependency_risk=0.50,
            r_and_d_protection_time=0.30,
            tasks_completed=50,
            tasks_total=100,
            tech_debt_tasks=35,
            overdue_tasks=40,
            single_point_dependencies=50,
            top_modules=[],
        )

        delivery_metrics = DeliveryHealthMetrics(
            overall_health_score=0.55,
            delivery_on_time_rate=0.60,
            version_success_rate=0.55,
            customer_issue_rate=0.25,
            implementation_rollback_risk=0.25,
            projects_on_time=6,
            projects_total=10,
            versions_success=5,
            versions_total=10,
        )

        # Execute
        challenges = report_service_no_ai._compile_challenges(
            rnd_metrics, delivery_metrics, date.today(), date.today()
        )

        # Verify
        assert len(challenges) >= 3  # Should have multiple challenges
        assert any("延期率" in c for c in challenges)
        assert any("技术债" in c for c in challenges)
        assert any("单点依赖" in c for c in challenges)
        assert any("客户问题" in c for c in challenges)

    @pytest.mark.asyncio
    async def test_generate_ai_recommendations(self, report_service, mock_ai_service):
        """Test AI recommendation generation."""
        # Setup metrics
        rnd_metrics = RnDHealthMetrics(
            overall_health_score=0.75,
            module_maturity_index=0.80,
            ontime_completion_rate=0.85,
            tech_debt_concentration=0.15,
            task_delay_rate=0.12,
            single_point_dependency_risk=0.25,
            r_and_d_protection_time=0.60,
            tasks_completed=80,
            tasks_total=100,
            tech_debt_tasks=15,
            overdue_tasks=12,
            single_point_dependencies=25,
            top_modules=[],
        )

        delivery_metrics = DeliveryHealthMetrics(
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

        # Setup AI response
        mock_ai_service.generate_text.return_value = """- 优化项目管理流程
- 加强团队协作和知识分享
- 增加自动化测试覆盖率"""

        # Execute
        recommendations = await report_service._generate_ai_recommendations(
            rnd_metrics, delivery_metrics
        )

        # Verify
        assert len(recommendations) == 3
        assert "优化项目管理流程" in recommendations
        assert "知识分享" in recommendations
