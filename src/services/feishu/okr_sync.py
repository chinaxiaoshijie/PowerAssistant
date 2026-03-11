"""OKR synchronization service for Feishu OKRs.

This module provides the business logic for synchronizing OKR data
from Feishu OKR to the local database.
"""

from datetime import datetime
from typing import List, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.feishu_tasks import FeishuOKR
from src.schemas.feishu import FeishuOKRRaw
from src.schemas.organization import SyncStats
from src.services.feishu.client import FeishuClient

logger = structlog.get_logger()


class OKRSyncService:
    """Service for synchronizing OKRs from Feishu.

    Handles both full and incremental synchronization of OKRs
    with proper transaction management and error handling.
    """

    def __init__(
        self,
        feishu_client: FeishuClient,
        db_session: AsyncSession,
    ):
        """Initialize OKR sync service.

        Args:
            feishu_client: Configured Feishu API client
            db_session: Database session for persistence
        """
        self._client = feishu_client
        self._session = db_session
        self._logger = logger.bind(component="OKRSyncService")

    async def full_sync(self) -> SyncStats:
        """Perform full synchronization of all OKRs.

        Returns:
            SyncStats with detailed statistics
        """
        self._logger.info("starting_full_sync")

        stats = SyncStats()

        try:
            # Fetch all OKRs from Feishu
            feishu_okrs = await self._client.list_okrs()
            stats.records_fetched = len(feishu_okrs)

            self._logger.info(
                "okrs_fetched_from_feishu",
                count=len(feishu_okrs),
            )

            # Get existing OKRs
            result = await self._session.execute(select(FeishuOKR))
            existing_okrs: List[FeishuOKR] = result.scalars().all()
            existing_map = {o.feishu_okr_id: o for o in existing_okrs}

            # Process each OKR
            for feishu_okr_data in feishu_okrs:
                try:
                    feishu_okr = FeishuOKRRaw(**feishu_okr_data)
                    await self._upsert_okr(feishu_okr, existing_map, stats)
                except Exception as e:
                    self._logger.error(
                        "okr_sync_failed",
                        okr_id=feishu_okr_data.get("okr_id", "unknown"),
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
            feishu_okrs = await self._client.list_okrs()
            stats.records_fetched = len(feishu_okrs)

            result = await self._session.execute(select(FeishuOKR))
            existing_okrs: List[FeishuOKR] = result.scalars().all()
            existing_map = {o.feishu_okr_id: o for o in existing_okrs}

            for feishu_okr_data in feishu_okrs:
                try:
                    feishu_okr = FeishuOKRRaw(**feishu_okr_data)
                    existing = existing_map.get(feishu_okr.okr_id)

                    if existing is None or self._okr_changed(existing, feishu_okr):
                        await self._upsert_okr(feishu_okr, existing_map, stats)
                except Exception as e:
                    self._logger.error(
                        "okr_sync_failed",
                        okr_id=feishu_okr_data.get("okr_id", "unknown"),
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

    async def _upsert_okr(
        self,
        feishu_okr: FeishuOKRRaw,
        existing_map: dict,
        stats: SyncStats,
    ) -> FeishuOKR:
        """Insert or update a single OKR."""
        existing = existing_map.get(feishu_okr.okr_id)

        if existing:
            # Update existing OKR
            existing.objective = feishu_okr.objective
            existing.key_results = feishu_okr.key_results
            existing.progress = feishu_okr.progress
            existing.owner_id = feishu_okr.owner_id
            existing.cycle = feishu_okr.cycle
            existing.parent_okr_id = feishu_okr.parent_okr_id
            existing.updated_at = datetime.utcnow()
            existing.sync_updated_at = datetime.utcnow()

            stats.records_updated += 1
            self._logger.debug("okr_updated", okr_id=feishu_okr.okr_id)
            return existing
        else:
            # Create new OKR
            okr = FeishuOKR(
                feishu_okr_id=feishu_okr.okr_id,
                objective=feishu_okr.objective,
                key_results=feishu_okr.key_results,
                progress=feishu_okr.progress,
                owner_id=feishu_okr.owner_id,
                cycle=feishu_okr.cycle,
                parent_okr_id=feishu_okr.parent_okr_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                sync_updated_at=datetime.utcnow(),
            )
            self._session.add(okr)
            stats.records_created += 1
            self._logger.debug("okr_created", okr_id=feishu_okr.okr_id)
            return okr

    def _okr_changed(
        self,
        existing: FeishuOKR,
        feishu_okr: FeishuOKRRaw,
    ) -> bool:
        """Check if OKR data has changed."""
        if existing.objective != feishu_okr.objective:
            return True
        if existing.progress != feishu_okr.progress:
            return True
        if feishu_okr.updated_time:
            update_time = datetime.fromtimestamp(feishu_okr.updated_time / 1000)
            if update_time > existing.sync_updated_at:
                return True

        return False
