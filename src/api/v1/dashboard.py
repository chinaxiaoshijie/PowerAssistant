"""Dashboard API for AI Intelligence System.

Provides endpoints for the web dashboard to display
intelligence items, reports, and statistics.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session
from src.models.ai_intelligence import (
    CrawlerSource,
    IntelligenceItem,
    IntelligenceReport,
)
from src.services.ai_intelligence import IntelligenceGatheringService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Templates directory
# templates = Jinja2Templates(directory="templates")


@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get dashboard statistics."""
    # Total items
    total_result = await db.execute(select(func.count()).select_from(IntelligenceItem))
    total_items = total_result.scalar()

    # Items today
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await db.execute(
        select(func.count())
        .select_from(IntelligenceItem)
        .where(IntelligenceItem.created_at >= today)
    )
    items_today = today_result.scalar()

    # Items by category
    category_result = await db.execute(
        select(IntelligenceItem.category, func.count())
        .group_by(IntelligenceItem.category)
    )
    by_category = {cat: count for cat, count in category_result.all()}

    # Items by source
    source_result = await db.execute(
        select(IntelligenceItem.source_type, func.count())
        .group_by(IntelligenceItem.source_type)
    )
    by_source = {src: count for src, count in source_result.all()}

    # Unprocessed items
    unprocessed_result = await db.execute(
        select(func.count())
        .select_from(IntelligenceItem)
        .where(IntelligenceItem.is_processed == False)
    )
    unprocessed = unprocessed_result.scalar()

    # High relevance items (unread)
    high_rel_result = await db.execute(
        select(func.count())
        .select_from(IntelligenceItem)
        .where(IntelligenceItem.relevance_score >= 0.7)
        .where(IntelligenceItem.is_read == False)
    )
    high_relevance_unread = high_rel_result.scalar()

    return {
        "total_items": total_items,
        "items_today": items_today,
        "unprocessed_items": unprocessed,
        "high_relevance_unread": high_relevance_unread,
        "by_category": by_category,
        "by_source": by_source,
    }


@router.get("/items")
async def list_intelligence_items(
    category: Optional[str] = None,
    source: Optional[str] = None,
    min_relevance: float = Query(0.0, ge=0, le=1),
    is_processed: Optional[bool] = None,
    is_read: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """List intelligence items with filters."""
    query = select(IntelligenceItem).order_by(desc(IntelligenceItem.created_at))

    # Apply filters
    if category:
        query = query.where(IntelligenceItem.category == category)
    if source:
        query = query.where(IntelligenceItem.source_type == source)
    if min_relevance > 0:
        query = query.where(IntelligenceItem.relevance_score >= min_relevance)
    if is_processed is not None:
        query = query.where(IntelligenceItem.is_processed == is_processed)
    if is_read is not None:
        query = query.where(IntelligenceItem.is_read == is_read)
    if search:
        query = query.where(
            IntelligenceItem.title.ilike(f"%{search}%") |
            IntelligenceItem.content.ilike(f"%{search}%") |
            IntelligenceItem.tags.contains([search])
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get items
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "items": [
            {
                "id": item.id,
                "title": item.title,
                "url": item.url,
                "source_type": item.source_type,
                "source_name": item.source_name,
                "category": item.category,
                "relevance_score": item.relevance_score,
                "summary": item.summary,
                "tags": item.tags,
                "is_processed": item.is_processed,
                "is_read": item.is_read,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ],
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(items) < total,
        },
    }


@router.get("/items/{item_id}")
async def get_intelligence_item(
    item_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get single intelligence item details."""
    result = await db.execute(
        select(IntelligenceItem).where(IntelligenceItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Mark as read
    if not item.is_read:
        item.is_read = True
        await db.commit()

    # Load analysis
    analyses = []
    for analysis in item.analysis_results:
        analyses.append({
            "id": analysis.id,
            "type": analysis.analysis_type,
            "model": analysis.model_used,
            "content": analysis.analysis_content,
            "action_items": analysis.action_items,
            "applicability_score": analysis.applicability_score,
            "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
        })

    return {
        "id": item.id,
        "title": item.title,
        "url": item.url,
        "content": item.content,
        "source_type": item.source_type,
        "source_name": item.source_name,
        "external_id": item.external_id,
        "author": item.author,
        "category": item.category,
        "summary": item.summary,
        "key_points": item.key_points,
        "relevance_score": item.relevance_score,
        "relevance_reasoning": item.relevance_reasoning,
        "tags": item.tags,
        "technologies": item.technologies,
        "metadata": item.metadata,
        "is_processed": item.is_processed,
        "is_read": item.is_read,
        "published_at": item.published_at.isoformat() if item.published_at else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "analyses": analyses,
    }


@router.post("/items/{item_id}/read")
async def mark_item_read(
    item_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Mark item as read."""
    result = await db.execute(
        select(IntelligenceItem).where(IntelligenceItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    item.is_read = True
    await db.commit()

    return {"success": True, "message": "Item marked as read"}


@router.get("/reports")
async def list_reports(
    report_type: Optional[str] = None,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """List generated reports."""
    query = select(IntelligenceReport).order_by(desc(IntelligenceReport.created_at))

    if report_type:
        query = query.where(IntelligenceReport.report_type == report_type)

    query = query.limit(limit)
    result = await db.execute(query)
    reports = result.scalars().all()

    return {
        "reports": [
            {
                "id": r.id,
                "type": r.report_type,
                "title": r.title,
                "period_start": r.period_start.isoformat() if r.period_start else None,
                "period_end": r.period_end.isoformat() if r.period_end else None,
                "summary": r.summary,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "highlight_count": len(r.highlights),
            }
            for r in reports
        ]
    }


@router.get("/reports/{report_id}")
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get report details."""
    result = await db.execute(
        select(IntelligenceReport).where(IntelligenceReport.id == report_id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "id": report.id,
        "type": report.report_type,
        "title": report.title,
        "period_start": report.period_start.isoformat() if report.period_start else None,
        "period_end": report.period_end.isoformat() if report.period_end else None,
        "summary": report.summary,
        "highlights": report.highlights,
        "category_breakdown": report.category_breakdown,
        "trends_analysis": report.trends_analysis,
        "status": report.status,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


@router.get("/sources")
async def list_sources(
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """List configured crawler sources."""
    result = await db.execute(select(CrawlerSource).order_by(CrawlerSource.name))
    sources = result.scalars().all()

    return {
        "sources": [
            {
                "id": s.id,
                "name": s.name,
                "type": s.source_type,
                "url": s.url,
                "is_active": s.is_active,
                "fetch_interval_hours": s.fetch_interval_hours,
                "last_fetched_at": s.last_fetched_at.isoformat() if s.last_fetched_at else None,
                "last_error": s.last_error,
            }
            for s in sources
        ]
    }


@router.post("/sources/{source_id}/toggle")
async def toggle_source(
    source_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Toggle source active status."""
    result = await db.execute(
        select(CrawlerSource).where(CrawlerSource.id == source_id)
    )
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    source.is_active = not source.is_active
    await db.commit()

    return {
        "success": True,
        "is_active": source.is_active,
        "message": f"Source {'activated' if source.is_active else 'deactivated'}",
    }


@router.post("/trigger-crawl")
async def trigger_manual_crawl(
    source_type: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Trigger manual crawl."""
    service = IntelligenceGatheringService(db)

    try:
        items = await service.crawl_and_store(source_type, limit=20)

        return {
            "success": True,
            "source": source_type,
            "items_crawled": len(items),
            "message": f"Successfully crawled {len(items)} items from {source_type}",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crawl failed: {str(e)}")
