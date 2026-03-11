"""Scheduled tasks for organization synchronization.

This module provides scheduled sync jobs using APScheduler.
"""

from datetime import datetime
from typing import Optional

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.config.settings import settings
from src.services.feishu.client import FeishuClient
from src.services.feishu.org_sync import OrganizationSyncService

logger = structlog.get_logger()

# Global scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


async def scheduled_org_sync():
    """Run scheduled incremental organization sync.

    This function is called by the scheduler to perform
    periodic synchronization of organization data.
    """
    logger.info("scheduled_sync_started")

    # Create database engine and session
    engine = create_async_engine(settings.database.url)
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with FeishuClient() as client:
            async with async_session() as session:
                sync_service = OrganizationSyncService(client, session)

                # Get last sync time for incremental sync
                last_sync = await sync_service.get_last_sync_time()

                if last_sync:
                    logger.info(
                        "running_incremental_sync",
                        since=last_sync.isoformat(),
                    )
                    result = await sync_service.incremental_sync(since=last_sync)
                else:
                    logger.info("no_previous_sync_running_full_sync")
                    result = await sync_service.full_sync()

                logger.info(
                    "scheduled_sync_completed",
                    sync_id=result.id,
                    status=result.status,
                    fetched=result.records_fetched,
                    created=result.records_created,
                    updated=result.records_updated,
                    duration_seconds=result.duration_seconds,
                )

    except Exception as e:
        logger.exception("scheduled_sync_failed", error=str(e))
        # Don't re-raise - let the scheduler continue

    finally:
        await engine.dispose()


def start_scheduler() -> AsyncIOScheduler:
    """Start the async scheduler with organization sync job.

    Returns:
        Running scheduler instance
    """
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        logger.warning("scheduler_already_running")
        return _scheduler

    _scheduler = AsyncIOScheduler()

    # Add organization sync job - runs every 6 hours
    _scheduler.add_job(
        scheduled_org_sync,
        trigger=IntervalTrigger(hours=settings.sync_interval_hours),
        id="org_sync",
        name="Organization Sync",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        "scheduler_started",
        sync_interval_hours=settings.sync_interval_hours,
    )

    return _scheduler


def stop_scheduler():
    """Stop the scheduler."""
    global _scheduler

    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        _scheduler = None
        logger.info("scheduler_stopped")
    else:
        logger.warning("scheduler_not_running")


def get_scheduler() -> Optional[AsyncIOScheduler]:
    """Get the current scheduler instance.

    Returns:
        Scheduler instance or None if not started
    """
    return _scheduler
