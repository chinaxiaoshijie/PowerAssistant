"""Project synchronization service for Feishu projects.

This module provides the business logic for synchronizing project data
from Feishu Project to the local database.
"""

from datetime import datetime
from typing import List, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.feishu_tasks import FeishuProject
from src.schemas.feishu import FeishuProjectRaw
from src.schemas.organization import SyncStats
from src.services.feishu.client import FeishuClient

logger = structlog.get_logger()


class ProjectSyncService:
    """Service for synchronizing projects from Feishu.

    Handles both full and incremental synchronization of projects
    with proper transaction management and error handling.
    """

    def __init__(
        self,
        feishu_client: FeishuClient,
        db_session: AsyncSession,
    ):
        """Initialize project sync service.

        Args:
            feishu_client: Configured Feishu API client
            db_session: Database session for persistence
        """
        self._client = feishu_client
        self._session = db_session
        self._logger = logger.bind(component="ProjectSyncService")

    async def full_sync(self) -> SyncStats:
        """Perform full synchronization of all projects.

        Returns:
            SyncStats with detailed statistics
        """
        self._logger.info("starting_full_sync")

        stats = SyncStats()

        try:
            # Fetch all projects from Feishu
            feishu_projects = await self._client.list_projects()
            stats.records_fetched = len(feishu_projects)

            self._logger.info(
                "projects_fetched_from_feishu",
                count=len(feishu_projects),
            )

            # Get existing projects
            result = await self._session.execute(select(FeishuProject))
            existing_projects: List[FeishuProject] = result.scalars().all()
            existing_map = {p.feishu_project_id: p for p in existing_projects}

            # Process each project
            for feishu_project_data in feishu_projects:
                try:
                    feishu_project = FeishuProjectRaw(**feishu_project_data)
                    await self._upsert_project(feishu_project, existing_map, stats)
                except Exception as e:
                    self._logger.error(
                        "project_sync_failed",
                        project_id=feishu_project_data.get("project_id", "unknown"),
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
        """Perform incremental synchronization."""
        if since is None:
            since = datetime.utcnow() - timedelta(hours=24)

        self._logger.info("starting_incremental_sync", since=since.isoformat())

        stats = SyncStats()

        try:
            feishu_projects = await self._client.list_projects()
            stats.records_fetched = len(feishu_projects)

            result = await self._session.execute(select(FeishuProject))
            existing_projects: List[FeishuProject] = result.scalars().all()
            existing_map = {p.feishu_project_id: p for p in existing_projects}

            for feishu_project_data in feishu_projects:
                try:
                    feishu_project = FeishuProjectRaw(**feishu_project_data)
                    existing = existing_map.get(feishu_project.project_id)

                    if existing is None or self._project_changed(existing, feishu_project):
                        await self._upsert_project(feishu_project, existing_map, stats)
                except Exception as e:
                    self._logger.error(
                        "project_sync_failed",
                        project_id=feishu_project_data.get("project_id", "unknown"),
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

    async def _upsert_project(
        self,
        feishu_project: FeishuProjectRaw,
        existing_map: dict,
        stats: SyncStats,
    ) -> FeishuProject:
        """Insert or update a single project."""
        existing = existing_map.get(feishu_project.project_id)

        # Convert timestamps
        start_date = None
        if feishu_project.start_time:
            start_date = datetime.fromtimestamp(feishu_project.start_time / 1000)

        end_date = None
        if feishu_project.end_time:
            end_date = datetime.fromtimestamp(feishu_project.end_time / 1000)

        # Parse status
        status_map = {
            "planning": "planning",
            "in_progress": "in_progress",
            "done": "done",
            "cancelled": "cancelled",
            "completed": "done",
        }
        status = status_map.get(feishu_project.status, feishu_project.status)

        # Determine risk level (simplified)
        risk_level = "low"
        if "high risk" in (feishu_project.description or "").lower():
            risk_level = "high"
        elif "medium risk" in (feishu_project.description or "").lower():
            risk_level = "medium"

        if existing:
            # Update existing project
            existing.name = feishu_project.name
            existing.description = feishu_project.description
            existing.status = status
            existing.start_date = start_date
            existing.end_date = end_date
            existing.owner_id = feishu_project.owner_id
            existing.member_ids = feishu_project.member_ids
            existing.risk_level = risk_level
            existing.updated_at = datetime.utcnow()
            existing.sync_updated_at = datetime.utcnow()

            stats.records_updated += 1
            self._logger.debug("project_updated", project_id=feishu_project.project_id)
            return existing
        else:
            # Create new project
            project = FeishuProject(
                feishu_project_id=feishu_project.project_id,
                name=feishu_project.name,
                description=feishu_project.description,
                status=status,
                start_date=start_date,
                end_date=end_date,
                owner_id=feishu_project.owner_id,
                member_ids=feishu_project.member_ids,
                risk_level=risk_level,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                sync_updated_at=datetime.utcnow(),
            )
            self._session.add(project)
            stats.records_created += 1
            self._logger.debug("project_created", project_id=feishu_project.project_id)
            return project

    def _project_changed(
        self,
        existing: FeishuProject,
        feishu_project: FeishuProjectRaw,
    ) -> bool:
        """Check if project data has changed."""
        if existing.name != feishu_project.name:
            return True
        if existing.status != feishu_project.status:
            return True
        if feishu_project.updated_time:
            update_time = datetime.fromtimestamp(feishu_project.updated_time / 1000)
            if update_time > existing.sync_updated_at:
                return True

        return False
