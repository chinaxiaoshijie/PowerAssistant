"""Scheduled tasks for AI intelligence gathering.

This module defines the actual task functions that are scheduled
to run periodically.
"""

from datetime import datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import AsyncSessionLocal
from src.services.ai_intelligence import IntelligenceGatheringService
from src.services.feishu import FeishuClient

logger = structlog.get_logger()


async def crawl_arxiv_task():
    """Task: Crawl arXiv for new papers."""
    logger.info("task_started", task="crawl_arxiv")

    async with AsyncSessionLocal() as session:
        try:
            service = IntelligenceGatheringService(session)

            # Crawl last 24 hours
            since = datetime.utcnow() - timedelta(hours=24)
            items = await service.crawl_and_store(
                source_type="arxiv",
                since=since,
                limit=50,
                auto_analyze=True,
            )

            logger.info(
                "task_completed",
                task="crawl_arxiv",
                items_crawled=len(items),
            )

        except Exception as e:
            logger.error("task_failed", task="crawl_arxiv", error=str(e))
            raise


async def crawl_github_task():
    """Task: Crawl GitHub trending repos."""
    logger.info("task_started", task="crawl_github")

    async with AsyncSessionLocal() as session:
        try:
            service = IntelligenceGatheringService(session)

            # Crawl trending repos
            since = datetime.utcnow() - timedelta(days=7)
            items = await service.crawl_and_store(
                source_type="github",
                since=since,
                limit=30,
                auto_analyze=True,
            )

            logger.info(
                "task_completed",
                task="crawl_github",
                items_crawled=len(items),
            )

        except Exception as e:
            logger.error("task_failed", task="crawl_github", error=str(e))
            raise


async def crawl_hackernews_task():
    """Task: Crawl Hacker News AI-related posts."""
    logger.info("task_started", task="crawl_hackernews")

    async with AsyncSessionLocal() as session:
        try:
            service = IntelligenceGatheringService(session)

            since = datetime.utcnow() - timedelta(hours=24)
            items = await service.crawl_and_store(
                source_type="hackernews",
                since=since,
                limit=20,
                auto_analyze=True,
            )

            logger.info(
                "task_completed",
                task="crawl_hackernews",
                items_crawled=len(items),
            )

        except Exception as e:
            logger.error("task_failed", task="crawl_hackernews", error=str(e))
            raise


async def analyze_pending_items_task():
    """Task: Analyze unprocessed items."""
    logger.info("task_started", task="analyze_pending")

    async with AsyncSessionLocal() as session:
        try:
            service = IntelligenceGatheringService(session)

            count = await service.analyze_pending_items(
                batch_size=20,
                min_relevance=0.3,  # Skip very low relevance
            )

            logger.info(
                "task_completed",
                task="analyze_pending",
                items_analyzed=count,
            )

        except Exception as e:
            logger.error("task_failed", task="analyze_pending", error=str(e))
            raise


async def generate_daily_report_task():
    """Task: Generate daily intelligence report."""
    logger.info("task_started", task="generate_daily_report")

    async with AsyncSessionLocal() as session:
        try:
            service = IntelligenceGatheringService(session)

            report = await service.generate_daily_report()

            logger.info(
                "task_completed",
                task="generate_daily_report",
                report_id=report.id,
                item_count=len(report.highlights),
            )

        except Exception as e:
            logger.error("task_failed", task="generate_daily_report", error=str(e))
            raise


async def send_daily_notification_task():
    """Task: Send daily report to Feishu."""
    logger.info("task_started", task="send_daily_notification")

    async with AsyncSessionLocal() as session:
        try:
            # Get today's report
            from sqlalchemy import select
            from src.models.ai_intelligence import IntelligenceReport

            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

            result = await session.execute(
                select(IntelligenceReport)
                .where(IntelligenceReport.report_type == "daily")
                .where(IntelligenceReport.created_at >= today)
                .order_by(IntelligenceReport.created_at.desc())
            )
            report = result.scalar_one_or_none()

            if not report:
                logger.warning("no_daily_report_found")
                return

            # Send to Feishu (requires configuration)
            # TODO: Implement Feishu notification service
            logger.info(
                "daily_report_ready_to_send",
                report_id=report.id,
                highlights_count=len(report.highlights),
            )

        except Exception as e:
            logger.error("task_failed", task="send_daily_notification", error=str(e))
            raise


async def cleanup_old_data_task():
    """Task: Cleanup old intelligence data."""
    logger.info("task_started", task="cleanup_old_data")

    async with AsyncSessionLocal() as session:
        try:
            from sqlalchemy import delete
            from src.models.ai_intelligence import IntelligenceItem

            # Delete items older than 90 days with low relevance
            cutoff = datetime.utcnow() - timedelta(days=90)

            result = await session.execute(
                delete(IntelligenceItem)
                .where(IntelligenceItem.created_at < cutoff)
                .where(IntelligenceItem.relevance_score < 0.3)
                .where(IntelligenceItem.is_read == False)
            )

            await session.commit()

            logger.info(
                "task_completed",
                task="cleanup_old_data",
                items_deleted=result.rowcount,
            )

        except Exception as e:
            logger.error("task_failed", task="cleanup_old_data", error=str(e))
            raise


# Task registry for scheduler
TASK_REGISTRY = {
    "crawl_arxiv": crawl_arxiv_task,
    "crawl_github": crawl_github_task,
    "crawl_hackernews": crawl_hackernews_task,
    "analyze_pending": analyze_pending_items_task,
    "generate_daily_report": generate_daily_report_task,
    "send_daily_notification": send_daily_notification_task,
    "cleanup_old_data": cleanup_old_data_task,
}
