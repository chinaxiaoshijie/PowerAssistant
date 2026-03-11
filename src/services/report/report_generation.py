"""Report generation service for weekly/monthly summaries."""

import json
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.ai_engine import AIEngineService
from src.services.metrics.rnd_health import RnDHealthMetricsService, RnDHealthMetrics
from src.services.metrics.delivery_health import DeliveryHealthMetricsService, DeliveryHealthMetrics
from src.models.ai_intelligence import IntelligenceItem

logger = structlog.get_logger()


class WeeklyReport:
    """Data class for weekly report."""

    def __init__(
        self,
        period_start: date,
        period_end: date,
        overall_health: float,
        key_metrics: Dict,
        achievements: List[str],
        challenges: List[str],
        recommendations: List[str],
        highlights: List[Dict],
        tasks_completed: int,
        tasks_in_progress: int,
        projects_on_track: int,
        projects_at_risk: int,
    ):
        self.period_start = period_start
        self.period_end = period_end
        self.overall_health = overall_health
        self.key_metrics = key_metrics
        self.achievements = achievements
        self.challenges = challenges
        self.recommendations = recommendations
        self.highlights = highlights
        self.tasks_completed = tasks_completed
        self.tasks_in_progress = tasks_in_progress
        self.projects_on_track = projects_on_track
        self.projects_at_risk = projects_at_risk

    def to_dict(self) -> Dict:
        return {
            "period": {
                "start": self.period_start.isoformat(),
                "end": self.period_end.isoformat(),
            },
            "overall_health": round(self.overall_health, 2),
            "key_metrics": self.key_metrics,
            "summary": {
                "tasks_completed": self.tasks_completed,
                "tasks_in_progress": self.tasks_in_progress,
                "projects_on_track": self.projects_on_track,
                "projects_at_risk": self.projects_at_risk,
            },
            "achievements": self.achievements,
            "challenges": self.challenges,
            "recommendations": self.recommendations,
            "highlights": self.highlights,
        }

    def to_markdown(self) -> str:
        """Generate Markdown formatted report."""
        md = f"""# 周报 - {self.period_start} 至 {self.period_end}

## 📊 核心指标

- 研发健康度: {self.overall_health:.0%}
- 完成任务: {self.tasks_completed} 个
- 进行中任务: {self.tasks_in_progress} 个
- 项目正常: {self.projects_on_track} 个
- 项目风险: {self.projects_at_risk} 个

## 📈 关键数据

"""
        for key, value in self.key_metrics.items():
            md += f"- {key}: {value}\n"

        md += "\n## ✅ 本周成就\n\n"
        for item in self.achievements:
            md += f"- {item}\n"

        md += "\n## ⚠️ 面临挑战\n\n"
        for item in self.challenges:
            md += f"- {item}\n"

        md += "\n## 💡 建议\n\n"
        for item in self.recommendations:
            md += f"- {item}\n"

        if self.highlights:
            md += "\n## 🌟 亮点\n\n"
            for highlight in self.highlights:
                md += f"- {highlight.get('title', '')}: {highlight.get('description', '')}\n"

        return md


class ReportGenerationService:
    """Report generation service."""

    def __init__(self, db_session: AsyncSession, ai_service: Optional[AIEngineService] = None):
        self._db = db_session
        self._ai = ai_service
        self._logger = logger.bind(component="ReportGenerationService")

    async def generate_weekly_report(
        self,
        week_offset: int = 0,
        employee_ids: Optional[List[str]] = None,
        project_ids: Optional[List[str]] = None,
    ) -> WeeklyReport:
        """Generate weekly report.

        Args:
            week_offset: Week offset from current week (0=current week, -1=last week)
            employee_ids: Filter by specific employee IDs
            project_ids: Filter by specific project IDs

        Returns:
            WeeklyReport instance
        """
        self._logger.info(
            "generating_weekly_report",
            week_offset=week_offset,
        )

        # Calculate period
        today = datetime.utcnow().date()
        start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
        end_of_week = start_of_week + timedelta(days=6)

        # Get R&D health metrics
        rnd_service = RnDHealthMetricsService(self._db)
        rnd_metrics = await rnd_service.calculate_health_metrics(
            start_date=start_of_week,
            end_date=end_of_week,
            employee_ids=employee_ids,
            project_ids=project_ids,
        )

        # Get delivery health metrics
        delivery_service = DeliveryHealthMetricsService(self._db)
        delivery_metrics = await delivery_service.calculate_health_metrics(
            start_date=start_of_week,
            end_date=end_of_week,
            project_ids=project_ids,
        )

        # Get recent intelligence highlights
        highlights = await self._get_recent_highlights(end_of_week)

        # Compile achievements and challenges
        achievements = await self._compile_achievements(
            rnd_metrics, delivery_metrics, start_of_week, end_of_week
        )

        challenges = await self._compile_challenges(
            rnd_metrics, delivery_metrics, start_of_week, end_of_week
        )

        # Use AI to generate recommendations if available
        recommendations = []
        if self._ai:
            recommendations = await self._generate_ai_recommendations(
                rnd_metrics, delivery_metrics
            )
        else:
            # Fallback to rule-based recommendations
            recommendations = self._generate_rule_based_recommendations(
                rnd_metrics, delivery_metrics
            )

        # Count tasks
        tasks_completed = rnd_metrics.tasks_completed
        tasks_in_progress = rnd_metrics.tasks_total - rnd_metrics.tasks_completed

        # Count projects
        projects_on_track = delivery_metrics.projects_total - delivery_metrics.projects_on_time
        projects_at_risk = delivery_metrics.projects_on_time

        report = WeeklyReport(
            period_start=start_of_week,
            period_end=end_of_week,
            overall_health=rnd_metrics.overall_health_score,
            key_metrics={
                "研发健康度": f"{rnd_metrics.overall_health_score:.0%}",
                "任务准时完成率": f"{rnd_metrics.ontime_completion_rate:.0%}",
                "技术债浓度": f"{rnd_metrics.tech_debt_concentration:.0%}",
                "任务延期率": f"{rnd_metrics.task_delay_rate:.0%}",
                "交付准时率": f"{delivery_metrics.delivery_on_time_rate:.0%}",
                "版本成功率": f"{delivery_metrics.version_success_rate:.0%}",
            },
            achievements=achievements,
            challenges=challenges,
            recommendations=recommendations,
            highlights=highlights,
            tasks_completed=tasks_completed,
            tasks_in_progress=tasks_in_progress,
            projects_on_track=projects_on_track,
            projects_at_risk=projects_at_risk,
        )

        self._logger.info(
            "weekly_report_generated",
            period_start=start_of_week,
            period_end=end_of_week,
            health_score=rnd_metrics.overall_health_score,
        )

        return report

    async def _get_recent_highlights(self, end_date: date) -> List[Dict]:
        """Get recent AI intelligence highlights."""
        start_date = end_date - timedelta(days=7)

        from sqlalchemy import select

        query = (
            select(IntelligenceItem)
            .where(IntelligenceItem.relevance_score >= 0.7)
            .where(IntelligenceItem.created_at >= start_date)
            .order_by(IntelligenceItem.relevance_score.desc())
            .limit(5)
        )

        result = await self._db.execute(query)
        items = result.scalars().all()

        return [
            {
                "title": item.title,
                "description": item.summary or "",
                "url": item.url,
                "relevance": item.relevance_score,
            }
            for item in items
        ]

    async def _compile_achievements(
        self,
        rnd_metrics: RnDHealthMetrics,
        delivery_metrics: DeliveryHealthMetrics,
        start_date: date,
        end_date: date,
    ) -> List[str]:
        """Compile achievements from metrics."""
        achievements = []

        if rnd_metrics.ontime_completion_rate >= 0.8:
            achievements.append(
                f"任务准时完成率达 {rnd_metrics.ontime_completion_rate:.0%}，表现优秀"
            )

        if rnd_metrics.overall_health_score >= 0.8:
            achievements.append(f"研发健康度保持在 {rnd_metrics.overall_health_score:.0%} 高水平")

        if delivery_metrics.delivery_on_time_rate >= 0.85:
            achievements.append(
                f"项目交付准时率达 {delivery_metrics.delivery_on_time_rate:.0%}"
            )

        if delivery_metrics.version_success_rate >= 0.9:
            achievements.append(
                f"版本成功率高达 {delivery_metrics.version_success_rate:.0%}"
            )

        if rnd_metrics.tech_debt_concentration <= 0.1:
            achievements.append(f"技术债控制良好，仅占 {rnd_metrics.tech_debt_concentration:.0%}")

        if not achievements:
            achievements.append("团队稳定运行，各项指标正常")

        return achievements

    async def _compile_challenges(
        self,
        rnd_metrics: RnDHealthMetrics,
        delivery_metrics: DeliveryHealthMetrics,
        start_date: date,
        end_date: date,
    ) -> List[str]:
        """Compile challenges from metrics."""
        challenges = []

        if rnd_metrics.task_delay_rate > 0.3:
            challenges.append(f"任务延期率较高（{rnd_metrics.task_delay_rate:.0%}）")

        if rnd_metrics.tech_debt_concentration > 0.25:
            challenges.append(
                f"技术债积累较多（{rnd_metrics.tech_debt_concentration:.0%}），需关注"
            )

        if rnd_metrics.single_point_dependency_risk > 0.4:
            challenges.append(
                f"单点依赖风险较高（{rnd_metrics.single_point_dependency_risk:.0%}）"
            )

        if delivery_metrics.implementation_rollback_risk > 0.2:
            challenges.append(
                f"项目实施风险较高（{delivery_metrics.implementation_rollback_risk:.0%}）"
            )

        if delivery_metrics.customer_issue_rate > 0.15:
            challenges.append(f"客户问题反馈率较高（{delivery_metrics.customer_issue_rate:.0%}）")

        if not challenges:
            challenges.append("暂无重大风险和挑战")

        return challenges

    async def _generate_ai_recommendations(
        self,
        rnd_metrics: RnDHealthMetrics,
        delivery_metrics: DeliveryHealthMetrics,
    ) -> List[str]:
        """Generate recommendations using AI."""
        prompt = f"""基于以下研发和交付健康指标，给出3-5条管理建议：

研发健康指标：
- 整体健康度: {rnd_metrics.overall_health_score:.0%}
- 任务准时完成率: {rnd_metrics.ontime_completion_rate:.0%}
- 技术债浓度: {rnd_metrics.tech_debt_concentration:.0%}
- 任务延期率: {rnd_metrics.task_delay_rate:.0%}
- 单点依赖风险: {rnd_metrics.single_point_dependency_risk:.0%}

交付健康指标：
- 整体健康度: {delivery_metrics.overall_health_score:.0%}
- 交付准时率: {delivery_metrics.delivery_on_time_rate:.0%}
- 版本成功率: {delivery_metrics.version_success_rate:.0%}
- 客户问题率: {delivery_metrics.customer_issue_rate:.0%}
- 实施回滚风险: {delivery_metrics.implementation_rollback_risk:.0%}

请用简洁的中文给出具体、可操作的建议。每条建议用“-”开头。"""
        try:
            response = await self._ai.generate_text(prompt, max_tokens=300)
            # Parse AI response into list of recommendations
            lines = response.strip().split("\n")
            recommendations = [line.strip()[2:] if line.strip().startswith("- ") else line.strip() for line in lines]
            return [r for r in recommendations if r]
        except Exception as e:
            self._logger.warning("ai_recommendations_failed", error=str(e))
            return self._generate_rule_based_recommendations(rnd_metrics, delivery_metrics)

    def _generate_rule_based_recommendations(
        self,
        rnd_metrics: RnDHealthMetrics,
        delivery_metrics: DeliveryHealthMetrics,
    ) -> List[str]:
        """Generate rule-based recommendations."""
        recommendations = []

        if rnd_metrics.tech_debt_concentration > 0.2:
            recommendations.append("建议安排技术债清理专项，减少长期维护成本")

        if rnd_metrics.single_point_dependency_risk > 0.3:
            recommendations.append("需要增加知识分享，降低单点依赖风险")

        if rnd_metrics.task_delay_rate > 0.25:
            recommendations.append("优化任务拆分和排期，提高执行效率")

        if delivery_metrics.customer_issue_rate > 0.1:
            recommendations.append("加强测试环节，降低客户问题反馈率")

        if delivery_metrics.implementation_rollback_risk > 0.15:
            recommendations.append("完善上线流程和回滚预案，降低实施风险")

        if rnd_metrics.r_and_d_protection_time < 0.5:
            recommendations.append("减少非紧急会议，保障研发专注时间")

        if not recommendations:
            recommendations.append("继续保持当前良好的工作节奏")

        return recommendations[:5]  # Limit to 5 recommendations
