"""R&D Health Metrics Calculation Engine.

Calculates R&D health indicators based on Feishu task/project data.
"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import structlog
from sqlalchemy import func, select, and_, or_, Float
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.feishu_tasks import FeishuTask, FeishuProject
from src.models.organization import Employee

logger = structlog.get_logger()


class RnDHealthMetrics:
    """Data class for R&D health metrics results."""

    def __init__(
        self,
        overall_health_score: float,
        module_maturity_index: float,
        ontime_completion_rate: float,
        tech_debt_concentration: float,
        task_delay_rate: float,
        single_point_dependency_risk: float,
        r_and_d_protection_time: float,
        tasks_completed: int,
        tasks_total: int,
        tech_debt_tasks: int,
        overdue_tasks: int,
        single_point_dependencies: int,
        top_modules: List[Dict],
    ):
        self.overall_health_score = overall_health_score
        self.module_maturity_index = module_maturity_index
        self.ontime_completion_rate = ontime_completion_rate
        self.tech_debt_concentration = tech_debt_concentration
        self.task_delay_rate = task_delay_rate
        self.single_point_dependency_risk = single_point_dependency_risk
        self.r_and_d_protection_time = r_and_d_protection_time
        self.tasks_completed = tasks_completed
        self.tasks_total = tasks_total
        self.tech_debt_tasks = tech_debt_tasks
        self.overdue_tasks = overdue_tasks
        self.single_point_dependencies = single_point_dependencies
        self.top_modules = top_modules


class RnDHealthMetricsService:
    """R&D Health Metrics Calculation Service.

    Calculates comprehensive R&D health indicators:

    Overall Health Score =
        0.30 × Module Maturity Index
      + 0.25 × Ontime Completion Rate
      + 0.20 × (1 - Tech Debt Concentration)
      + 0.15 × R&D Protection Time
      + 0.10 × (1 - Single Point Dependency Risk)
    """

    def __init__(self, db_session: AsyncSession):
        self._db = db_session
        self._logger = logger.bind(component="RnDHealthMetricsService")

    async def calculate_health_metrics(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        employee_ids: Optional[List[str]] = None,
        project_ids: Optional[List[str]] = None,
    ) -> RnDHealthMetrics:
        """Calculate R&D health metrics for a time period.

        Args:
            start_date: Start date for calculation (default: 30 days ago)
            end_date: End date for calculation (default: today)
            employee_ids: Filter by specific employee IDs
            project_ids: Filter by specific project IDs

        Returns:
            RnDHealthMetrics with all calculated indicators
        """
        self._logger.info(
            "calculating_rnd_health_metrics",
            start_date=start_date,
            end_date=end_date,
        )

        if start_date is None:
            start_date = (datetime.utcnow().date() - timedelta(days=30))
        if end_date is None:
            end_date = datetime.utcnow().date()

        # Calculate all metrics
        tasks_completed = await self._get_completed_tasks_count(
            start_date, end_date, employee_ids, project_ids
        )
        tasks_total = await self._get_total_tasks_count(
            start_date, end_date, employee_ids, project_ids
        )

        # Calculate completion rate
        ontime_completion_rate = self._calculate_ontime_completion_rate(
            tasks_completed, tasks_total
        )

        # Calculate task delay rate
        task_delay_rate = await self._calculate_task_delay_rate(
            start_date, end_date, employee_ids, project_ids
        )

        # Calculate module maturity index (proxy: completion rate + no delays)
        module_maturity_index = self._calculate_module_maturity_index(
            ontime_completion_rate, task_delay_rate
        )

        # Calculate tech debt concentration
        tech_debt_count, total_count = await self._get_tech_debt_stats(
            start_date, end_date, employee_ids, project_ids
        )
        tech_debt_concentration = self._calculate_tech_debt_concentration(
            tech_debt_count, total_count
        )

        # Calculate single point dependency risk
        single_point_deps = await self._calculate_single_point_dependencies(
            employee_ids, project_ids
        )

        # Calculate R&D protection time (estimated from task distribution)
        r_and_d_protection_time = await self._calculate_r_and_d_protection_time(
            start_date, end_date, employee_ids
        )

        # Calculate overall health score
        overall_health_score = self._calculate_overall_health_score(
            module_maturity_index=module_maturity_index,
            ontime_completion_rate=ontime_completion_rate,
            tech_debt_concentration=tech_debt_concentration,
            r_and_d_protection_time=r_and_d_protection_time,
            single_point_dependency_risk=single_point_deps,
        )

        # Get top modules by progress
        top_modules = await self._get_top_modules(project_ids)

        metrics = RnDHealthMetrics(
            overall_health_score=overall_health_score,
            module_maturity_index=module_maturity_index,
            ontime_completion_rate=ontime_completion_rate,
            tech_debt_concentration=tech_debt_concentration,
            task_delay_rate=task_delay_rate,
            single_point_dependency_risk=single_point_deps,
            r_and_d_protection_time=r_and_d_protection_time,
            tasks_completed=tasks_completed,
            tasks_total=tasks_total,
            tech_debt_tasks=tech_debt_count,
            overdue_tasks=await self._get_overdue_tasks_count(
                start_date, end_date, employee_ids, project_ids
            ),
            single_point_dependencies=int(single_point_deps * 100),  # convert to percentage
            top_modules=top_modules,
        )

        self._logger.info(
            "rnd_health_metrics_calculated",
            overall_score=overall_health_score,
            tasks_completed=tasks_completed,
            tasks_total=tasks_total,
        )

        return metrics

    async def _get_completed_tasks_count(
        self,
        start_date: date,
        end_date: date,
        employee_ids: Optional[List[str]],
        project_ids: Optional[List[str]],
    ) -> int:
        """Get count of completed tasks in time range."""
        query = (
            select(func.count(FeishuTask.id))
            .where(FeishuTask.status == "done")
            .where(FeishuTask.completed_at >= start_date)
            .where(FeishuTask.completed_at <= datetime.combine(end_date, datetime.max.time()))
        )

        if employee_ids:
            # Need to filter by assignee_ids JSON field
            from sqlalchemy import cast, JSON
            query = query.where(cast(FeishuTask.assignee_ids, JSON).contains(employee_ids))

        if project_ids:
            query = query.where(FeishuTask.project_id.in_(project_ids))

        result = await self._db.execute(query)
        return result.scalar() or 0

    async def _get_total_tasks_count(
        self,
        start_date: date,
        end_date: date,
        employee_ids: Optional[List[str]],
        project_ids: Optional[List[str]],
    ) -> int:
        """Get total tasks created in time range."""
        query = (
            select(func.count(FeishuTask.id))
            .where(FeishuTask.created_at >= start_date)
            .where(FeishuTask.created_at <= datetime.combine(end_date, datetime.max.time()))
        )

        if employee_ids:
            from sqlalchemy import cast, JSON
            query = query.where(cast(FeishuTask.assignee_ids, JSON).contains(employee_ids))

        if project_ids:
            query = query.where(FeishuTask.project_id.in_(project_ids))

        result = await self._db.execute(query)
        return result.scalar() or 0

    def _calculate_ontime_completion_rate(self, completed: int, total: int) -> float:
        """Calculate on-time completion rate."""
        if total == 0:
            return 0.0
        return completed / total

    async def _calculate_task_delay_rate(
        self,
        start_date: date,
        end_date: date,
        employee_ids: Optional[List[str]],
        project_ids: Optional[List[str]],
    ) -> float:
        """Calculate task delay rate."""
        overdue_query = (
            select(func.count(FeishuTask.id))
            .where(FeishuTask.status == "done")
            .where(FeishuTask.completed_at > FeishuTask.due_date)
            .where(FeishuTask.completed_at >= start_date)
            .where(FeishuTask.completed_at <= datetime.combine(end_date, datetime.max.time()))
        )

        if employee_ids:
            from sqlalchemy import cast, JSON
            overdue_query = overdue_query.where(
                cast(FeishuTask.assignee_ids, JSON).contains(employee_ids)
            )

        if project_ids:
            overdue_query = overdue_query.where(FeishuTask.project_id.in_(project_ids))

        total_query = (
            select(func.count(FeishuTask.id))
            .where(FeishuTask.status == "done")
            .where(FeishuTask.completed_at >= start_date)
            .where(FeishuTask.completed_at <= datetime.combine(end_date, datetime.max.time()))
        )

        if employee_ids:
            from sqlalchemy import cast, JSON
            total_query = total_query.where(
                cast(FeishuTask.assignee_ids, JSON).contains(employee_ids)
            )

        if project_ids:
            total_query = total_query.where(FeishuTask.project_id.in_(project_ids))

        overdue_result = await self._db.execute(overdue_query)
        total_result = await self._db.execute(total_query)

        overdue = overdue_result.scalar() or 0
        total = total_result.scalar() or 0

        if total == 0:
            return 0.0
        return overdue / total

    def _calculate_module_maturity_index(
        self,
        completion_rate: float,
        delay_rate: float,
    ) -> float:
        """Calculate module maturity index.

        Proxy metric based on completion rate and delay avoidance.
        """
        maturity = completion_rate * (1 - delay_rate)
        return min(max(maturity, 0.0), 1.0)

    async def _get_tech_debt_stats(
        self,
        start_date: date,
        end_date: date,
        employee_ids: Optional[List[str]],
        project_ids: Optional[List[str]],
    ) -> tuple[int, int]:
        """Get tech debt task statistics."""
        tech_debt_query = (
            select(func.count(FeishuTask.id))
            .where(FeishuTask.is_tech_debt == True)
            .where(FeishuTask.created_at >= start_date)
            .where(FeishuTask.created_at <= datetime.combine(end_date, datetime.max.time()))
        )

        if employee_ids:
            from sqlalchemy import cast, JSON
            tech_debt_query = tech_debt_query.where(
                cast(FeishuTask.assignee_ids, JSON).contains(employee_ids)
            )

        if project_ids:
            tech_debt_query = tech_debt_query.where(FeishuTask.project_id.in_(project_ids))

        total_query = (
            select(func.count(FeishuTask.id))
            .where(FeishuTask.created_at >= start_date)
            .where(FeishuTask.created_at <= datetime.combine(end_date, datetime.max.time()))
        )

        if employee_ids:
            from sqlalchemy import cast, JSON
            total_query = total_query.where(
                cast(FeishuTask.assignee_ids, JSON).contains(employee_ids)
            )

        if project_ids:
            total_query = total_query.where(FeishuTask.project_id.in_(project_ids))

        tech_debt_result = await self._db.execute(tech_debt_query)
        total_result = await self._db.execute(total_query)

        return tech_debt_result.scalar() or 0, total_result.scalar() or 0

    def _calculate_tech_debt_concentration(
        self,
        tech_debt_count: int,
        total_count: int,
    ) -> float:
        """Calculate tech debt concentration."""
        if total_count == 0:
            return 0.0
        return tech_debt_count / total_count

    async def _calculate_single_point_dependencies(
        self,
        employee_ids: Optional[List[str]],
        project_ids: Optional[List[str]],
    ) -> float:
        """Calculate single point dependency risk.

        Approximation: percentage of tasks assigned to only one person
        """
        query = select(FeishuTask).where(func.json_array_length(FeishuTask.assignee_ids) == 1)

        if employee_ids:
            from sqlalchemy import cast, JSON
            query = query.where(cast(FeishuTask.assignee_ids, JSON).contains(employee_ids))

        if project_ids:
            query = query.where(FeishuTask.project_id.in_(project_ids))

        result = await self._db.execute(query)
        single_assignee_tasks = result.scalars().all()

        # Total tasks
        total_query = select(FeishuTask)
        if employee_ids:
            from sqlalchemy import cast, JSON
            total_query = total_query.where(
                cast(FeishuTask.assignee_ids, JSON).contains(employee_ids)
            )
        if project_ids:
            total_query = total_query.where(FeishuTask.project_id.in_(project_ids))

        total_result = await self._db.execute(total_query)
        total_tasks = total_result.scalars().all()

        if len(total_tasks) == 0:
            return 0.0

        return len(single_assignee_tasks) / len(total_tasks)

    async def _calculate_r_and_d_protection_time(
        self,
        start_date: date,
        end_date: date,
        employee_ids: Optional[List[str]],
    ) -> float:
        """Estimate R&D protection time.

        Approximation: time spent on tasks without urgent meetings/interruptions
        Simplified version: assume 60% of time is protected if no urgent tasks
        """
        # Count urgent/high priority tasks
        urgent_query = (
            select(func.count(FeishuTask.id))
            .where(
                or_(
                    FeishuTask.priority == "p0",
                    FeishuTask.priority == "p1",
                )
            )
            .where(FeishuTask.status != "done")
            .where(FeishuTask.created_at >= start_date)
            .where(FeishuTask.created_at <= datetime.combine(end_date, datetime.max.time()))
        )

        if employee_ids:
            from sqlalchemy import cast, JSON
            urgent_query = urgent_query.where(
                cast(FeishuTask.assignee_ids, JSON).contains(employee_ids)
            )

        total_query = (
            select(func.count(FeishuTask.id))
            .where(FeishuTask.created_at >= start_date)
            .where(FeishuTask.created_at <= datetime.combine(end_date, datetime.max.time()))
        )

        if employee_ids:
            from sqlalchemy import cast, JSON
            total_query = total_query.where(
                cast(FeishuTask.assignee_ids, JSON).contains(employee_ids)
            )

        urgent_result = await self._db.execute(urgent_query)
        total_result = await self._db.execute(total_query)

        urgent = urgent_result.scalar() or 0
        total = total_result.scalar() or 0

        # Protection time decreases with more urgent tasks
        if total == 0:
            return 0.6  # default 60%

        urgent_ratio = urgent / total
        protection_time = max(0.6 - (urgent_ratio * 0.4), 0.2)  # between 20% and 60%

        return protection_time

    def _calculate_overall_health_score(
        self,
        module_maturity_index: float,
        ontime_completion_rate: float,
        tech_debt_concentration: float,
        r_and_d_protection_time: float,
        single_point_dependency_risk: float,
    ) -> float:
        """Calculate overall R&D health score.

        Overall Health Score =
            0.30 × Module Maturity Index
          + 0.25 × Ontime Completion Rate
          + 0.20 × (1 - Tech Debt Concentration)
          + 0.15 × R&D Protection Time
          + 0.10 × (1 - Single Point Dependency Risk)
        """
        score = (
            0.30 * module_maturity_index
            + 0.25 * ontime_completion_rate
            + 0.20 * (1.0 - tech_debt_concentration)
            + 0.15 * r_and_d_protection_time
            + 0.10 * (1.0 - single_point_dependency_risk)
        )

        return min(max(score, 0.0), 1.0)

    async def _get_overdue_tasks_count(
        self,
        start_date: date,
        end_date: date,
        employee_ids: Optional[List[str]],
        project_ids: Optional[List[str]],
    ) -> int:
        """Get count of overdue tasks."""
        query = (
            select(func.count(FeishuTask.id))
            .where(FeishuTask.is_overdue == True)
            .where(FeishuTask.status != "done")
            .where(FeishuTask.created_at >= start_date)
            .where(FeishuTask.created_at <= datetime.combine(end_date, datetime.max.time()))
        )

        if employee_ids:
            from sqlalchemy import cast, JSON
            query = query.where(cast(FeishuTask.assignee_ids, JSON).contains(employee_ids))

        if project_ids:
            query = query.where(FeishuTask.project_id.in_(project_ids))

        result = await self._db.execute(query)
        return result.scalar() or 0

    async def _get_top_modules(
        self,
        project_ids: Optional[List[str]],
    ) -> List[Dict]:
        """Get top modules by progress."""
        query = select(FeishuProject).where(FeishuProject.status != "done")

        if project_ids:
            query = query.where(FeishuProject.feishu_project_id.in_(project_ids))

        query = query.order_by(FeishuProject.progress.desc()).limit(5)

        result = await self._db.execute(query)
        projects = result.scalars().all()

        return [
            {
                "id": p.id,
                "name": p.name,
                "progress": p.progress,
                "status": p.status,
                "risk_level": p.risk_level,
            }
            for p in projects
        ]

    async def get_trend_data(
        self,
        days: int = 30,
        interval_days: int = 7,
    ) -> List[Dict]:
        """Get health score trend over time.

        Args:
            days: Number of days to look back
            interval_days: Interval for each data point

        Returns:
            List of health score data points with timestamps
        """
        self._logger.info(
            "calculating_health_trend",
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
                    "module_maturity": metrics.module_maturity_index,
                    "completion_rate": metrics.ontime_completion_rate,
                    "tech_debt": metrics.tech_debt_concentration,
                    "tasks_completed": metrics.tasks_completed,
                    "tasks_total": metrics.tasks_total,
                }
            )

        return trend
