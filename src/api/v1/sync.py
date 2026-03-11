"""Sync control API routes.

This module provides endpoints for managing and monitoring
organization synchronization operations.
"""

from typing import List, Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, get_feishu_client
from src.models.sync_log import SyncLog
from src.schemas.organization import (
    SyncLogResponse,
    SyncResultResponse,
    SyncStats,
    SyncStatusResponse,
)
from src.services.feishu.client import FeishuClient
from src.services.feishu.org_sync import OrganizationSyncService

logger = structlog.get_logger()
router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/full", response_model=SyncResultResponse)
async def trigger_full_sync(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    client: FeishuClient = Depends(get_feishu_client),
) -> SyncResultResponse:
    """Trigger full organization synchronization.

    This operation can take several minutes depending on organization size.
    It runs in the background and returns immediately.

    Args:
        background_tasks: FastAPI background tasks
        db: Database session
        client: Feishu API client

    Returns:
        Sync result with statistics
    """
    logger.info("triggering_full_sync")

    # Run sync synchronously for now (can be made async later)
    sync_service = OrganizationSyncService(client, db)
    result = await sync_service.full_sync()

    return SyncResultResponse(
        sync_id=result.id,
        sync_type=result.sync_type,
        entity_type=result.entity_type,
        stats=SyncStats(
            records_fetched=result.records_fetched,
            records_created=result.records_created,
            records_updated=result.records_updated,
            records_deactivated=result.records_deactivated,
        ),
        status=result.status,
        started_at=result.started_at,
        completed_at=result.completed_at,
        duration_seconds=result.duration_seconds,
    )


@router.post("/incremental", response_model=SyncResultResponse)
async def trigger_incremental_sync(
    db: AsyncSession = Depends(get_db),
    client: FeishuClient = Depends(get_feishu_client),
) -> SyncResultResponse:
    """Trigger incremental organization synchronization.

    Only syncs records changed since the last successful sync.

    Args:
        db: Database session
        client: Feishu API client

    Returns:
        Sync result with statistics
    """
    logger.info("triggering_incremental_sync")

    sync_service = OrganizationSyncService(client, db)

    # Get last sync time
    last_sync = await sync_service.get_last_sync_time()

    result = await sync_service.incremental_sync(since=last_sync)

    return SyncResultResponse(
        sync_id=result.id,
        sync_type=result.sync_type,
        entity_type=result.entity_type,
        stats=SyncStats(
            records_fetched=result.records_fetched,
            records_created=result.records_created,
            records_updated=result.records_updated,
            records_deactivated=result.records_deactivated,
        ),
        status=result.status,
        started_at=result.started_at,
        completed_at=result.completed_at,
        duration_seconds=result.duration_seconds,
    )


@router.get("/history", response_model=List[SyncLogResponse])
async def get_sync_history(
    entity_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> List[SyncLogResponse]:
    """Get synchronization history.

    Args:
        entity_type: Filter by entity type (department/employee)
        status: Filter by status (success/failed/partial)
        limit: Maximum number of records to return
        db: Database session

    Returns:
        List of sync log entries
    """
    logger.info(
        "getting_sync_history",
        entity_type=entity_type,
        status=status,
        limit=limit,
    )

    query = select(SyncLog).order_by(desc(SyncLog.started_at))

    if entity_type:
        query = query.where(SyncLog.entity_type == entity_type)

    if status:
        query = query.where(SyncLog.status == status)

    query = query.limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        SyncLogResponse(
            id=log.id,
            sync_type=log.sync_type,
            entity_type=log.entity_type,
            records_fetched=log.records_fetched,
            records_created=log.records_created,
            records_updated=log.records_updated,
            records_deactivated=log.records_deactivated,
            started_at=log.started_at,
            completed_at=log.completed_at,
            status=log.status,
            error_message=log.error_message,
            duration_seconds=log.duration_seconds,
        )
        for log in logs
    ]


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(
    db: AsyncSession = Depends(get_db),
) -> SyncStatusResponse:
    """Get current synchronization status.

    Args:
        db: Database session

    Returns:
        Current sync status including last sync time and health
    """
    logger.info("getting_sync_status")

    # Get last successful sync
    result = await db.execute(
        select(SyncLog)
        .where(SyncLog.status == "success")
        .order_by(desc(SyncLog.completed_at))
        .limit(1)
    )
    last_sync = result.scalar_one_or_none()

    # Check if sync is in progress
    in_progress_result = await db.execute(
        select(SyncLog)
        .where(SyncLog.status == "in_progress")
        .order_by(desc(SyncLog.started_at))
        .limit(1)
    )
    in_progress = in_progress_result.scalar_one_or_none()

    # Get recent syncs (last 10)
    recent_result = await db.execute(
        select(SyncLog)
        .order_by(desc(SyncLog.started_at))
        .limit(10)
    )
    recent_syncs = recent_result.scalars().all()

    # Determine health
    health = "unknown"
    if last_sync:
        # Check if last sync was recent (within 24 hours)
        from datetime import datetime, timedelta

        if datetime.utcnow() - last_sync.completed_at < timedelta(hours=24):
            health = "healthy"
        elif datetime.utcnow() - last_sync.completed_at < timedelta(hours=48):
            health = "degraded"
        else:
            health = "failed"

    # Calculate next scheduled sync
    next_scheduled = None
    if last_sync and last_sync.completed_at:
        from datetime import timedelta

        next_scheduled = last_sync.completed_at + timedelta(hours=6)

    return SyncStatusResponse(
        last_sync_time=last_sync.completed_at if last_sync else None,
        next_scheduled_sync=next_scheduled,
        is_syncing=in_progress is not None,
        recent_syncs=[
            SyncLogResponse(
                id=log.id,
                sync_type=log.sync_type,
                entity_type=log.entity_type,
                records_fetched=log.records_fetched,
                records_created=log.records_created,
                records_updated=log.records_updated,
                records_deactivated=log.records_deactivated,
                started_at=log.started_at,
                completed_at=log.completed_at,
                status=log.status,
                error_message=log.error_message,
                duration_seconds=log.duration_seconds,
            )
            for log in recent_syncs
        ],
        health=health,
    )


@router.get("/{sync_id}", response_model=SyncLogResponse)
async def get_sync_detail(
    sync_id: int,
    db: AsyncSession = Depends(get_db),
) -> SyncLogResponse:
    """Get detailed information about a specific sync.

    Args:
        sync_id: Sync log ID
        db: Database session

    Returns:
        Sync log details

    Raises:
        HTTPException: If sync log not found
    """
    logger.info("getting_sync_detail", sync_id=sync_id)

    result = await db.execute(
        select(SyncLog).where(SyncLog.id == sync_id)
    )
    log = result.scalar_one_or_none()

    if not log:
        logger.warning("sync_log_not_found", sync_id=sync_id)
        raise HTTPException(status_code=404, detail="Sync log not found")

    return SyncLogResponse(
        id=log.id,
        sync_type=log.sync_type,
        entity_type=log.entity_type,
        records_fetched=log.records_fetched,
        records_created=log.records_created,
        records_updated=log.records_updated,
        records_deactivated=log.records_deactivated,
        started_at=log.started_at,
        completed_at=log.completed_at,
        status=log.status,
        error_message=log.error_message,
        duration_seconds=log.duration_seconds,
    )
