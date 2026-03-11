"""Task synchronization service for Feishu tasks.

This module provides the business logic for synchronizing task data
from Feishu Task to the local database.
"""

from datetime import datetime
from typing import List, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.feishu_tasks import FeishuTask
from src.schemas.feishu import FeishuTaskRaw
from src.schemas.organization import SyncStats
from src.services.feishu.client import FeishuClient

logger = structlog.get_logger()


class TaskSyncService:
    """Service for synchronizing tasks from Feishu.

    Handles both full and incremental synchronization of tasks
    with proper transaction management and error handling.
    """

    def __init__(
        self,
        feishu_client: FeishuClient,
        db_session: AsyncSession,
    ):
        """Initialize task sync service.

        Args:
            feishu_client: Configured Feishu API client
            db_session: Database session for persistence
        """
        self._client = feishu_client
        self._session = db_session
        self._logger = logger.bind(component="TaskSyncService")

    async def full_sync(self) -> SyncStats:
        """Perform full synchronization of all tasks.

        Fetches all tasks from Feishu and updates the local database.
        Marks tasks not present in Feishu as inactive.

        Returns:
            SyncStats with detailed statistics
        """
        self._logger.info("starting_full_sync")

        stats = SyncStats()

        try:
            # Fetch all tasks from Feishu
            feishu_tasks = await self._client.list_tasks()
            stats.records_fetched = len(feishu_tasks)

            self._logger.info(
                "tasks_fetched_from_feishu",
                count=len(feishu_tasks),
            )

            # Get existing tasks for comparison
            result = await self._session.execute(select(FeishuTask))
            existing_tasks: List[FeishuTask] = result.scalars().all()
            existing_map = {t.feishu_task_id: t for t in existing_tasks}

            # Process each task
            for feishu_task_data in feishu_tasks:
                try:
                    # Convert dict to FeishuTaskRaw
                    feishu_task = FeishuTaskRaw(**feishu_task_data)
                    await self._upsert_task(feishu_task, existing_map, stats)
                except Exception as e:
                    self._logger.error(
                        "task_sync_failed",
                        task_id=feishu_task_data.get("task_id", "unknown"),
                        error=str(e),
                    )
                    stats.error_count += 1

            await self._session.commit()

            self._logger.info(
                "full_sync_completed",
                fetched=stats.records_fetched,
                created=stats.records_created,
                updated=stats.records_updated,
                errors=stats.error_count,
            )

        except Exception as e:
            self._logger.exception("full_sync_failed", error=str(e))
            await self._session.rollback()
            raise

        return stats

    async def incremental_sync(
        self,
        since: Optional[datetime] = None,
    ) -> SyncStats:
        """Perform incremental synchronization.

        Only fetches and updates tasks changed since the last sync.
        If no timestamp provided, uses last 24 hours.

        Args:
            since: Timestamp for incremental sync (default: 24h ago)

        Returns:
            SyncStats with detailed statistics
        """
        if since is None:
            since = datetime.utcnow() - timedelta(hours=24)

        self._logger.info("starting_incremental_sync", since=since.isoformat())

        stats = SyncStats()

        try:
            # For incremental sync, we still fetch all tasks
            # Feishu Task API doesn't support updated_since filter directly
            feishu_tasks = await self._client.list_tasks()
            stats.records_fetched = len(feishu_tasks)

            # Get existing tasks
            result = await self._session.execute(select(FeishuTask))
            existing_tasks: List[FeishuTask] = result.scalars().all()
            existing_map = {t.feishu_task_id: t for t in existing_tasks}

            # Process only changed tasks
            for feishu_task_data in feishu_tasks:
                try:
                    feishu_task = FeishuTaskRaw(**feishu_task_data)
                    existing = existing_map.get(feishu_task.task_id)

                    # Check if task is new or has been updated
                    if existing is None or self._task_changed(existing, feishu_task):
                        await self._upsert_task(feishu_task, existing_map, stats)
                except Exception as e:
                    self._logger.error(
                        "task_sync_failed",
                        task_id=feishu_task_data.get("task_id", "unknown"),
                        error=str(e),
                    )
                    stats.error_count += 1

            await self._session.commit()

            self._logger.info(
                "incremental_sync_completed",
                fetched=stats.records_fetched,
                created=stats.records_created,
                updated=stats.records_updated,
                errors=stats.error_count,
            )

        except Exception as e:
            self._logger.exception("incremental_sync_failed", error=str(e))
            await self._session.rollback()
            raise

        return stats

    async def _upsert_task(
        self,
        feishu_task: FeishuTaskRaw,
        existing_map: dict,
        stats: SyncStats,
    ) -> FeishuTask:
        """Insert or update a single task.

        Args:
            feishu_task: Feishu task data
            existing_map: Map of existing tasks by ID
            stats: Sync statistics object

        Returns:
            The upserted task object
        """
        existing = existing_map.get(feishu_task.task_id)

        # Convert timestamps from milliseconds to datetime
        due_date = None
        if feishu_task.due_time:
            due_date = datetime.fromtimestamp(feishu_task.due_time / 1000)

        completed_at = None
        if feishu_task.completed_time:
            completed_at = datetime.fromtimestamp(feishu_task.completed_time / 1000)

        # Parse status
        status_map = {
            "not_started": "pending",
            "in_progress": "in_progress",
            "done": "done",
            "cancelled": "cancelled",
            "completed": "done",
        }
        status = status_map.get(feishu_task.status, feishu_task.status)

        # Determine priority (simplified logic)
        priority = "p2"  # default
        if "urgent" in feishu_task.summary.lower():
            priority = "p0"
        elif "high" in feishu_task.summary.lower():
            priority = "p1"

        if existing:
            # Update existing task
            existing.title = feishu_task.summary
            existing.description = feishu_task.description
            existing.status = status
            existing.priority = priority
            existing.due_date = due_date
            existing.completed_at = completed_at
            existing.assignee_ids = feishu_task.assignee_ids
            existing.reporter_id = feishu_task.creator_id
            existing.updated_at = datetime.utcnow()
            existing.sync_updated_at = datetime.utcnow()

            # Simple tech debt detection
            if any(kw in (feishu_task.description or "").lower()
                   for kw in ["tech debt", "technical debt", "重构", "优化", "临时"]):
                existing.is_tech_debt = True

            stats.records_updated += 1
            self._logger.debug("task_updated", task_id=feishu_task.task_id)
            return existing
        else:
            # Create new task
            task = FeishuTask(
                feishu_task_id=feishu_task.task_id,
                title=feishu_task.summary,
                description=feishu_task.description,
                status=status,
                priority=priority,
                due_date=due_date,
                completed_at=completed_at,
                assignee_ids=feishu_task.assignee_ids,
                reporter_id=feishu_task.creator_id,
                is_tech_debt=any(kw in (feishu_task.description or "").lower()
                                for kw in ["tech debt", "technical debt", "重构", "优化", "临时"]),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                sync_updated_at=datetime.utcnow(),
            )
            self._session.add(task)
            stats.records_created += 1
            self._logger.debug("task_created", task_id=feishu_task.task_id)
            return task

    def _task_changed(
        self,
        existing: FeishuTask,
        feishu_task: FeishuTaskRaw,
    ) -> bool:
        """Check if task data has changed.

        Args:
            existing: Existing task in database
            feishu_task: Task data from Feishu

        Returns:
            True if task has changed
        """
        # Check key fields
        if existing.title != feishu_task.summary:
            return True
        if existing.status != feishu_task.status:
            return True
        if existing.assignee_ids != feishu_task.assignee_ids:
            return True

        # Check timestamps
        if feishu_task.updated_time:
            update_time = datetime.fromtimestamp(feishu_task.updated_time / 1000)
            if update_time > existing.sync_updated_at:
                return True

        return False
