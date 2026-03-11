"""Task scheduler for automated intelligence gathering.

Uses APScheduler for periodic task execution.
"""

import asyncio
from datetime import datetime
from typing import Callable, Dict, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.database import database
from src.services.ai_intelligence import IntelligenceGatheringService
from src.services.feishu.client import FeishuClient
from src.services.feishu.org_sync import OrganizationSyncService
from src.services.feishu.task_sync import TaskSyncService
from src.services.feishu.project_sync import ProjectSyncService
from src.services.feishu.okr_sync import OKRSyncService

import structlog

logger = structlog.get_logger()


class IntelligenceScheduler:
    """Scheduler for AI intelligence gathering tasks.

    Manages periodic tasks:
    - Crawling from various sources
    - Analyzing collected items
    - Generating reports
    - Sending notifications
    """

    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = AsyncIOScheduler()
        self._logger = logger.bind(component="IntelligenceScheduler")
        self._jobs: Dict[str, str] = {}  # job_name -> job_id

    async def _get_db_session(self) -> AsyncSession:
        """Get database session."""
        if database.session_factory is None:
            database.initialize()
        return database.session_factory()

    async def _feishu_sync_task(self) -> None:
        """Sync Feishu organization data."""
        self._logger.info("starting_feishu_sync_task")

        try:
            async with FeishuClient() as client:
                session = await self._get_db_session()
                try:
                    sync_service = OrganizationSyncService(session, client)

                    # Sync departments
                    dept_result = await sync_service.sync_departments()
                    self._logger.info(
                        "feishu_departments_synced",
                        count=dept_result.get("count", 0),
                    )

                    # Sync employees
                    emp_result = await sync_service.sync_employees()
                    self._logger.info(
                        "feishu_employees_synced",
                        count=emp_result.get("count", 0),
                    )

                    await session.commit()
                    self._logger.info("feishu_sync_task_completed")

                except Exception as e:
                    await session.rollback()
                    raise
                finally:
                    await session.close()

        except Exception as e:
            self._logger.error("feishu_sync_task_failed", error=str(e))

    async def _feishu_task_sync_task(self) -> None:
        """Sync Feishu tasks data."""
        self._logger.info("starting_feishu_task_sync_task")

        try:
            async with FeishuClient() as client:
                session = await self._get_db_session()
                try:
                    sync_service = TaskSyncService(session, client)
                    stats = await sync_service.full_sync()
                    self._logger.info(
                        "feishu_tasks_synced",
                        fetched=stats.records_fetched,
                        created=stats.records_created,
                        updated=stats.records_updated,
                    )
                    await session.commit()
                except Exception as e:
                    await session.rollback()
                    raise
                finally:
                    await session.close()

        except Exception as e:
            self._logger.error("feishu_task_sync_task_failed", error=str(e))

    async def _feishu_project_sync_task(self) -> None:
        """Sync Feishu projects data."""
        self._logger.info("starting_feishu_project_sync_task")

        try:
            async with FeishuClient() as client:
                session = await self._get_db_session()
                try:
                    sync_service = ProjectSyncService(session, client)
                    stats = await sync_service.full_sync()
                    self._logger.info(
                        "feishu_projects_synced",
                        fetched=stats.records_fetched,
                        created=stats.records_created,
                        updated=stats.records_updated,
                    )
                    await session.commit()
                except Exception as e:
                    await session.rollback()
                    raise
                finally:
                    await session.close()

        except Exception as e:
            self._logger.error("feishu_project_sync_task_failed", error=str(e))

    async def _feishu_okr_sync_task(self) -> None:
        """Sync Feishu OKRs data."""
        self._logger.info("starting_feishu_okr_sync_task")

        try:
            async with FeishuClient() as client:
                session = await self._get_db_session()
                try:
                    sync_service = OKRSyncService(session, client)
                    stats = await sync_service.full_sync()
                    self._logger.info(
                        "feishu_okrs_synced",
                        fetched=stats.records_fetched,
                        created=stats.records_created,
                        updated=stats.records_updated,
                    )
                    await session.commit()
                except Exception as e:
                    await session.rollback()
                    raise
                finally:
                    await session.close()

        except Exception as e:
            self._logger.error("feishu_okr_sync_task_failed", error=str(e))

    def schedule_feishu_sync(
        self,
        hours: int = 1,
    ) -> None:
        """Schedule Feishu organization sync.

        Args:
            hours: Interval in hours
        """
        job_id = "feishu_sync"

        job = self.scheduler.add_job(
            func=self._feishu_sync_task,
            trigger=IntervalTrigger(hours=hours),
            id=job_id,
            name="Sync Feishu organization",
            replace_existing=True,
        )

        self._jobs[job_id] = job.id
        self._logger.info(
            "scheduled_feishu_sync",
            hours=hours,
            job_id=job.id,
        )

    def schedule_feishu_task_sync(
        self,
        hours: int = 2,
    ) -> None:
        """Schedule Feishu task sync.

        Args:
            hours: Interval in hours
        """
        job_id = "feishu_task_sync"

        job = self.scheduler.add_job(
            func=self._feishu_task_sync_task,
            trigger=IntervalTrigger(hours=hours),
            id=job_id,
            name="Sync Feishu tasks",
            replace_existing=True,
        )

        self._jobs[job_id] = job.id
        self._logger.info(
            "scheduled_feishu_task_sync",
            hours=hours,
            job_id=job.id,
        )

    def schedule_feishu_project_sync(
        self,
        hours: int = 4,
    ) -> None:
        """Schedule Feishu project sync.

        Args:
            hours: Interval in hours
        """
        job_id = "feishu_project_sync"

        job = self.scheduler.add_job(
            func=self._feishu_project_sync_task,
            trigger=IntervalTrigger(hours=hours),
            id=job_id,
            name="Sync Feishu projects",
            replace_existing=True,
        )

        self._jobs[job_id] = job.id
        self._logger.info(
            "scheduled_feishu_project_sync",
            hours=hours,
            job_id=job.id,
        )

    def schedule_feishu_okr_sync(
        self,
        hours: int = 6,
    ) -> None:
        """Schedule Feishu OKR sync.

        Args:
            hours: Interval in hours
        """
        job_id = "feishu_okr_sync"

        job = self.scheduler.add_job(
            func=self._feishu_okr_sync_task,
            trigger=IntervalTrigger(hours=hours),
            id=job_id,
            name="Sync Feishu OKRs",
            replace_existing=True,
        )

        self._jobs[job_id] = job.id
        self._logger.info(
            "scheduled_feishu_okr_sync",
            hours=hours,
            job_id=job.id,
        )

    def setup_default_schedule(self) -> None:
        """Setup default task schedule."""
        self._logger.info("setting_up_default_schedule")

        # Crawl arXiv every 6 hours
        self.schedule_crawl("arxiv", hours=6, limit=50)

        # Crawl GitHub every 6 hours (offset by 1 hour)
        self.schedule_crawl("github", hours=6, limit=30)

        # Crawl Hacker News every 3 hours
        self.schedule_crawl("hackernews", hours=3, limit=20)

        # Analyze pending items every 30 minutes
        self.schedule_analysis(minutes=30, batch_size=20)

        # Generate daily report at 9:00 AM
        self.schedule_daily_report(hour=9, minute=0)

        # Generate weekly report on Monday at 10:00 AM
        self.schedule_weekly_report(day_of_week="mon", hour=10, minute=0)

        # Run AI agent analysis every 24 hours
        self.schedule_agent_analysis(hours=24)

        # Sync Feishu organization every 1 hour
        self.schedule_feishu_sync(hours=1)

        # Sync Feishu tasks every 2 hours
        self.schedule_feishu_task_sync(hours=2)

        # Sync Feishu projects every 4 hours
        self.schedule_feishu_project_sync(hours=4)

        # Sync Feishu OKRs every 6 hours
        self.schedule_feishu_okr_sync(hours=6)

        self._logger.info("default_schedule_configured")

        try:
            async with FeishuClient() as client:
                async with await self._get_db_session() as session:
                    sync_service = OrganizationSyncService(session, client)

                    # Sync departments
                    dept_result = await sync_service.sync_departments()
                    self._logger.info(
                        "feishu_departments_synced",
                        count=dept_result.get("count", 0),
                    )

                    # Sync employees
                    emp_result = await sync_service.sync_employees()
                    self._logger.info(
                        "feishu_employees_synced",
                        count=emp_result.get("count", 0),
                    )

                    await session.commit()
                    self._logger.info("feishu_sync_task_completed")

        except Exception as e:
            self._logger.error("feishu_sync_task_failed", error=str(e))
        """Crawl task wrapper.

        Args:
            source_type: Type of source to crawl
            limit: Maximum items to fetch
        """
        self._logger.info("starting_crawl_task", source=source_type)

        session = await self._get_db_session()
        try:
            service = IntelligenceGatheringService(session)
            items = await service.crawl_and_store(
                source_type=source_type,
                limit=limit,
                auto_analyze=True,
            )
            self._logger.info(
                "crawl_task_completed",
                source=source_type,
                items_count=len(items),
            )
        except Exception as e:
            self._logger.error(
                "crawl_task_failed",
                source=source_type,
                error=str(e),
            )
        finally:
            await session.close()

    async def _analyze_task(self, batch_size: int = 20) -> None:
        """Analyze pending items task.

        Args:
            batch_size: Number of items to analyze
        """
        self._logger.info("starting_analysis_task")

        session = await self._get_db_session()
        try:
            service = IntelligenceGatheringService(session)
            count = await service.analyze_pending_items(batch_size=batch_size)
            self._logger.info(
                "analysis_task_completed",
                items_analyzed=count,
            )
        except Exception as e:
            self._logger.error("analysis_task_failed", error=str(e))
        finally:
            await session.close()

    async def _daily_report_task(self) -> None:
        """Generate daily report task."""
        self._logger.info("starting_daily_report_task")

        session = await self._get_db_session()
        try:
            service = IntelligenceGatheringService(session)
            report = await service.generate_daily_report()
            self._logger.info(
                "daily_report_generated",
                report_id=report.id,
                items_included=len(report.highlights),
            )

            # Send notification via Feishu
            try:
                async with FeishuClient() as client:
                    from src.services.feishu.notification import FeishuNotificationService

                    notification_service = FeishuNotificationService(feishu_client=client)

                    # TODO: 配置接收群组ID
                    chat_id = "oc_xxx"  # 需要替换为实际的群聊ID

                    await notification_service.send_daily_report(
                        chat_id=chat_id,
                        report_data={
                            "title": "AI情报日报",
                            "summary": report.summary or "今日无重要情报更新",
                            "highlights": report.highlights,
                            "stats": {
                                "items_today": len(report.highlights),
                                "high_relevance": len([h for h in report.highlights if h.get("relevance_score", 0) > 0.8]),
                                "unread": 0,
                            },
                        },
                    )

                    self._logger.info("daily_report_notification_sent")

            except Exception as e:
                self._logger.warning("daily_report_notification_failed", error=str(e))

        except Exception as e:
            self._logger.error("daily_report_task_failed", error=str(e))
        finally:
            await session.close()

    async def _weekly_report_task(self) -> None:
        """Generate weekly report task."""
        self._logger.info("starting_weekly_report_task")

        session = await self._get_db_session()
        try:
            from src.services.report.report_generation import ReportGenerationService

            service = ReportGenerationService(session)
            report = await service.generate_weekly_report(week_offset=-1)  # 上周报告

            self._logger.info(
                "weekly_report_generated",
                period=f"{report.period_start} to {report.period_end}",
                health_score=report.overall_health,
            )

            # Send notification via Feishu
            try:
                async with FeishuClient() as client:
                    from src.services.feishu.notification import FeishuNotificationService

                    notification_service = FeishuNotificationService(feishu_client=client)

                    # TODO: 配置接收群组ID
                    chat_id = "oc_xxx"  # 需要替换为实际的群聊ID

                    await notification_service.send_weekly_report(
                        chat_id=chat_id,
                        report=report,
                    )

                    self._logger.info("weekly_report_notification_sent")

            except Exception as e:
                self._logger.warning("weekly_report_notification_failed", error=str(e))

        except Exception as e:
            self._logger.error("weekly_report_task_failed", error=str(e))
        finally:
            await session.close()

    async def _agent_analysis_task(self) -> None:
        """Run all AI agents and send analysis results."""
        self._logger.info("starting_agent_analysis_task")

        session = await self._get_db_session()
        try:
            from src.services.ai_intelligence.agents import run_all_agents

            results = await run_all_agents(session)

            self._logger.info(
                "agent_analysis_completed",
                agents=list(results.get("agents", {}).keys()),
            )

            # Send agent analysis via Feishu
            try:
                async with FeishuClient() as client:
                    from src.services.feishu.notification import FeishuNotificationService

                    notification_service = FeishuNotificationService(feishu_client=client)

                    # TODO: 配置接收群组ID
                    chat_id = "oc_xxx"  # 需要替换为实际的群聊ID

                    for agent_type, agent_result in results.get("agents", {}).items():
                        agent_name = agent_result.get("agent", agent_type)
                        data = agent_result.get("data", {})
                        status = data.get("status")

                        if status == "success":
                            await notification_service.send_ai_intelligence_summary(
                                chat_id=chat_id,
                                agent_name=agent_name,
                                summary=data.get("ai_summary", "暂无分析结果"),
                                insights=data.get("insights", []),
                            )

                    self._logger.info("agent_analysis_notification_sent")

            except Exception as e:
                self._logger.warning("agent_analysis_notification_failed", error=str(e))

        except Exception as e:
            self._logger.error("agent_analysis_task_failed", error=str(e))
        finally:
            await session.close()

    def schedule_crawl(
        self,
        source_type: str,
        hours: int = 6,
        limit: int = 50,
    ) -> None:
        """Schedule periodic crawling.

        Args:
            source_type: Type of source (arxiv/github/hackernews)
            hours: Interval in hours
            limit: Maximum items per crawl
        """
        job_id = f"crawl_{source_type}"

        job = self.scheduler.add_job(
            func=self._crawl_task,
            trigger=IntervalTrigger(hours=hours),
            id=job_id,
            name=f"Crawl {source_type}",
            replace_existing=True,
            args=[source_type, limit],
        )

        self._jobs[job_id] = job.id
        self._logger.info(
            "scheduled_crawl",
            source=source_type,
            hours=hours,
            job_id=job.id,
        )

    def schedule_analysis(
        self,
        minutes: int = 30,
        batch_size: int = 20,
    ) -> None:
        """Schedule periodic analysis.

        Args:
            minutes: Interval in minutes
            batch_size: Items to analyze per run
        """
        job_id = "analyze_pending"

        job = self.scheduler.add_job(
            func=self._analyze_task,
            trigger=IntervalTrigger(minutes=minutes),
            id=job_id,
            name="Analyze pending items",
            replace_existing=True,
            args=[batch_size],
        )

        self._jobs[job_id] = job.id
        self._logger.info(
            "scheduled_analysis",
            minutes=minutes,
            batch_size=batch_size,
            job_id=job.id,
        )

    def schedule_daily_report(
        self,
        hour: int = 9,
        minute: int = 0,
    ) -> None:
        """Schedule daily report generation.

        Args:
            hour: Hour of day (0-23)
            minute: Minute of hour (0-59)
        """
        job_id = "daily_report"

        job = self.scheduler.add_job(
            func=self._daily_report_task,
            trigger=CronTrigger(hour=hour, minute=minute),
            id=job_id,
            name="Generate daily report",
            replace_existing=True,
        )

        self._jobs[job_id] = job.id
        self._logger.info(
            "scheduled_daily_report",
            time=f"{hour:02d}:{minute:02d}",
            job_id=job.id,
        )

    def schedule_weekly_report(
        self,
        day_of_week: str = "mon",
        hour: int = 10,
        minute: int = 0,
    ) -> None:
        """Schedule weekly report generation.

        Args:
            day_of_week: Day of week (mon/tue/wed/thu/fri/sat/sun)
            hour: Hour of day (0-23)
            minute: Minute of hour (0-59)
        """
        job_id = "weekly_report"

        job = self.scheduler.add_job(
            func=self._weekly_report_task,
            trigger=CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute),
            id=job_id,
            name="Generate weekly report",
            replace_existing=True,
        )

        self._jobs[job_id] = job.id
        self._logger.info(
            "scheduled_weekly_report",
            day=day_of_week,
            time=f"{hour:02d}:{minute:02d}",
            job_id=job.id,
        )

    def schedule_agent_analysis(
        self,
        hours: int = 24,
    ) -> None:
        """Schedule AI agent analysis.

        Args:
            hours: Interval in hours
        """
        job_id = "agent_analysis"

        job = self.scheduler.add_job(
            func=self._agent_analysis_task,
            trigger=IntervalTrigger(hours=hours),
            id=job_id,
            name="Run AI agent analysis",
            replace_existing=True,
        )

        self._jobs[job_id] = job.id
        self._logger.info(
            "scheduled_agent_analysis",
            hours=hours,
            job_id=job.id,
        )

    def start(self) -> None:
        """Start the scheduler."""
        self.scheduler.start()
        self._logger.info("scheduler_started")

    def shutdown(self) -> None:
        """Shutdown the scheduler."""
        self.scheduler.shutdown()
        self._logger.info("scheduler_shutdown")

    def get_jobs(self) -> list:
        """Get list of scheduled jobs."""
        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
            }
            for job in self.scheduler.get_jobs()
        ]

    def pause_job(self, job_id: str) -> None:
        """Pause a scheduled job."""
        self.scheduler.pause_job(job_id)
        self._logger.info("job_paused", job_id=job_id)

    def resume_job(self, job_id: str) -> None:
        """Resume a paused job."""
        self.scheduler.resume_job(job_id)
        self._logger.info("job_resumed", job_id=job_id)

    def remove_job(self, job_id: str) -> None:
        """Remove a scheduled job."""
        self.scheduler.remove_job(job_id)
        if job_id in self._jobs:
            del self._jobs[job_id]
        self._logger.info("job_removed", job_id=job_id)


# Global scheduler instance
scheduler = IntelligenceScheduler()
