"""Delivery health metrics calculation for product delivery tracking."""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import structlog
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.feishu_tasks import FeishuProject, FeishuTask
from src.models.organization import Employee

logger = structlog.get_logger()


class DeliveryHealthMetrics:
    """Data class for delivery health metrics results."""

    def __init__(
        self,
        overall_health_score: float,
        delivery_on_time_rate: float,
        version_success_rate: float,
        customer_issue_rate: float,
        implementation_rollback_risk: float,
        projects_on_time: int,
        projects_total: int,
        versions_success: int,
        versions_total: int,
    ):
        self.overall_health_score = overall_health_score
        self.delivery_on_time_rate = delivery_on_time_rate
        self.version_success_rate = version_success_rate
        self.customer_issue_rate = customer_issue_rate
        self.implementation_rollback_risk = implementation_rollback_risk
        self.projects_on_time = projects_on_time
        self.projects_total = projects_total
        self.versions_success = versions_success
        self.versions_total = versions_total


class DeliveryHealthMetricsService:
    """Delivery Health Metrics Calculation Service.

    Calculates comprehensive delivery health indicators:

    Overall Health Score =
        0.40 × (1 - Project Delay Rate)
      + 0.30 × Version Success Rate
      + 0.20 × (1 - Customer Issue Rate)
      + 0.10 × Delivery On-Time Rate
    """

    def __init__(self, db_session: AsyncSession):
        self._db = db_session
        self._logger = logger.bind(component="DeliveryHealthMetricsService")

    async def calculate_health_metrics(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        project_ids: Optional[List[str]] = None,
    ) -> DeliveryHealthMetrics:
        """Calculate delivery health metrics for a time period.

        Args:
            start_date: Start date for calculation (default: 30 days ago)
            end_date: End date for calculation (default: today)
            project_ids: Filter by specific project IDs

        Returns:
            DeliveryHealthMetrics with all calculated indicators
        """
        self._logger.info(
            "calculating_delivery_health_metrics",
            start_date=start_date,
            end_date=end_date,
        )

        if start_date is None:
            start_date = (datetime.utcnow().date() - timedelta(days=30))
        if end_date is None:
            end_date = datetime.utcnow().date()

        # Calculate project on-time rate
        projects_on_time, projects_total = await self._get_project_on_time_stats(
            start_date, end_date, project_ids
        )
        delivery_on_time_rate = self._calculate_delivery_on_time_rate(
            projects_on_time, projects_total
        )

        # Calculate version success rate
        versions_success, versions_total = await self._get_version_success_stats(
            start_date, end_date, project_ids
        )
        version_success_rate = self._calculate_version_success_rate(
            versions_success, versions_total
        )

        # Calculate customer issue rate (estimated from bug reports in tasks)
        customer_issues = await self._get_customer_issue_count(
            start_date, end_date, project_ids
        )
        customer_issue_rate = self._calculate_customer_issue_rate(
            customer_issues, versions_total
        )

        # Calculate implementation rollback risk
        rollback_risk = await self._calculate_rollback_risk(
            start_date, end_date, project_ids
        )

        # Calculate overall health score
        overall_health_score = self._calculate_overall_health_score(
            delivery_on_time_rate=delivery_on_time_rate,
            version_success_rate=version_success_rate,
            customer_issue_rate=customer_issue_rate,
            rollback_risk=rollback_risk,
        )

        metrics = DeliveryHealthMetrics(
            overall_health_score=overall_health_score,
            delivery_on_time_rate=delivery_on_time_rate,
            version_success_rate=version_success_rate,
            customer_issue_rate=customer_issue_rate,
            implementation_rollback_risk=rollback_risk,
            projects_on_time=projects_on_time,
            projects_total=projects_total,
            versions_success=versions_success,
            versions_total=versions_total,
        )

        self._logger.info(
            "delivery_health_metrics_calculated",
            overall_score=overall_health_score,
            projects_on_time=projects_on_time,
            projects_total=projects_total,
        )

        return metrics

    async def _get_project_on_time_stats(
        self,
        start_date: date,
        end_date: date,
        project_ids: Optional[List[str]],
    ) -> tuple[int, int]:
        """Get count of on-time and total projects."""
        on_time_query = (
            select(func.count(FeishuProject.id))
            .where(FeishuProject.status == "done")
            .where(FeishuProject.actual_end_date <= FeishuProject.end_date)
            .where(FeishuProject.actual_end_date >= start_date)
            .where(FeishuProject.actual_end_date <= datetime.combine(end_date, datetime.max.time()))
        )

        if project_ids:
            on_time_query = on_time_query.where(
                FeishuProject.feishu_project_id.in_(project_ids)
            )

        total_query = (
            select(func.count(FeishuProject.id))
            .where(FeishuProject.status == "done")
            .where(FeishuProject.actual_end_date >= start_date)
            .where(FeishuProject.actual_end_date <= datetime.combine(end_date, datetime.max.time()))
        )

        if project_ids:
            total_query = total_query.where(
                FeishuProject.feishu_project_id.in_(project_ids)
            )

        on_time_result = await self._db.execute(on_time_query)
        total_result = await self._db.execute(total_query)

        return on_time_result.scalar() or 0, total_result.scalar() or 0

    def _calculate_delivery_on_time_rate(
        self,
        on_time: int,
        total: int,
    ) -> float:
        """Calculate delivery on-time rate."""
        if total == 0:
            return 0.0
        return on_time / total

    async def _get_version_success_stats(
        self,
        start_date: date,
        end_date: date,
        project_ids: Optional[List[str]],
    ) -> tuple[int, int]:
        """Get count of successful and total version deployments.

        For now, we approximate this using project completion data.
        In future, this should come from deployment logs or CI/CD data.
        """
        # Approximate: successful versions = completed projects without high risk
        success_query = (
            select(func.count(FeishuProject.id))
            .where(FeishuProject.status == "done")
            .where(FeishuProject.risk_level.in_(["low", "medium"]))
            .where(FeishuProject.actual_end_date >= start_date)
            .where(FeishuProject.actual_end_date <= datetime.combine(end_date, datetime.max.time()))
        )

        if project_ids:
            success_query = success_query.where(
                FeishuProject.feishu_project_id.in_(project_ids)
            )

        total_query = (
            select(func.count(FeishuProject.id))
            .where(FeishuProject.status == "done")
            .where(FeishuProject.actual_end_date >= start_date)
            .where(FeishuProject.actual_end_date <= datetime.combine(end_date, datetime.max.time()))
        )

        if project_ids:
            total_query = total_query.where(
                FeishuProject.feishu_project_id.in_(project_ids)
            )

        success_result = await self._db.execute(success_query)
        total_result = await self._db.execute(total_query)

        return success_result.scalar() or 0, total_result.scalar() or 0

    def _calculate_version_success_rate(
        self,
        success: int,
        total: int,
    ) -> float:
        """Calculate version success rate."""
        if total == 0:
            return 0.0
        return success / total

    async def _get_customer_issue_count(
        self,
        start_date: date,
        end_date: date,
        project_ids: Optional[List[str]],
    ) -> int:
        """Get count of customer-reported issues.

        For now, we approximate this by counting tasks with "bug" or "issue" labels.
        """
        query = (
            select(func.count(FeishuTask.id))
            .where(FeishuTask.status == "done")
            .where(
                (FeishuTask.labels.op("?")("bug"))
                | (FeishuTask.labels.op("?")("issue"))
            )
            .where(FeishuTask.completed_at >= start_date)
            .where(FeishuTask.completed_at <= datetime.combine(end_date, datetime.max.time()))
        )

        if project_ids:
            query = query.where(FeishuTask.project_id.in_(project_ids))

        result = await self._db.execute(query)
        return result.scalar() or 0

    def _calculate_customer_issue_rate(
        self,
        customer_issues: int,
        versions_total: int,
    ) -> float:
        """Calculate customer issue rate."""
        if versions_total == 0:
            return 0.0
        return customer_issues / versions_total

    async def _calculate_rollback_risk(
        self,
        start_date: date,
        end_date: date,
        project_ids: Optional[List[str]],
    ) -> float:
        """Calculate implementation rollback risk.

        Based on failed projects or projects with high risk level
        """
        failed_query = (
            select(func.count(FeishuProject.id))
            .where(
                or_(
                    FeishuProject.status == "cancelled",
                    FeishuProject.risk_level == "critical",
                )
            )
            .where(FeishuProject.updated_at >= start_date)
            .where(FeishuProject.updated_at <= datetime.combine(end_date, datetime.max.time()))
        )

        if project_ids:
            failed_query = failed_query.where(
                FeishuProject.feishu_project_id.in_(project_ids)
            )

        total_query = (
            select(func.count(FeishuProject.id))
            .where(FeishuProject.status.in_(["done", "cancelled"]))
            .where(FeishuProject.updated_at >= start_date)
            .where(FeishuProject.updated_at <= datetime.combine(end_date, datetime.max.time()))
        )

        if project_ids:
            total_query = total_query.where(
                FeishuProject.feishu_project_id.in_(project_ids)
            )

        failed_result = await self._db.execute(failed_query)
        total_result = await self._db.execute(total_query)

        failed = failed_result.scalar() or 0
        total = total_result.scalar() or 0

        if total == 0:
            return 0.0

        return failed / total

    def _calculate_overall_health_score(
        self,
        delivery_on_time_rate: float,
        version_success_rate: float,
        customer_issue_rate: float,
        rollback_risk: float,
    ) -> float:
        """Calculate overall delivery health score.

        Overall Health Score =
            0.40 × (1 - Project Delay Rate)
          + 0.30 × Version Success Rate
          + 0.20 × (1 - Customer Issue Rate)
          + 0.10 × Delivery On-Time Rate
        """
        score = (
            0.40 * delivery_on_time_rate
            + 0.30 * version_success_rate
            + 0.20 * (1.0 - customer_issue_rate)
            + 0.10 * delivery_on_time_rate
        )

        return min(max(score, 0.0), 1.0)

    async def get_trend_data(
        self,
        days: int = 30,
        interval_days: int = 7,
    ) -> List[Dict]:
        """Get delivery health trend over time.

        Args:
            days: Number of days to look back
            interval_days: Interval for each data point

        Returns:
            List of health score data points with timestamps
        """
        self._logger.info(
            "calculating_delivery_trend",
            days=days,
            interval_days=interval_days,
        )

        trend = []
        today = datetime.utcnow().date()

        for i in range(0, days, interval_days):
            end_date = today - timedelta(days=i)
            start_date = end_date - timedelta(days=interval_days)

            metrics = await self.calculate_health_metrics(
                start_date=start_date,
                end_date=end_date,
            )

            trend.append(
                {
                    "date": end_date.isoformat(),
                    "overall_score": metrics.overall_health_score,
                    "on_time_rate": metrics.delivery_on_time_rate,
                    "version_success": metrics.version_success_rate,
                    "customer_issues": metrics.customer_issue_rate,
                    "projects_total": metrics.projects_total,
                }
            )

        return trend
