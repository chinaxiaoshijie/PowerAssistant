"""API endpoints for R&D and Delivery Health Metrics."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.services.metrics.rnd_health import RnDHealthMetricsService
from src.services.metrics.delivery_health import DeliveryHealthMetricsService

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/rnd-health")
async def get_rnd_health_metrics(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    employee_ids: Optional[str] = Query(None, description="Comma-separated employee IDs"),
    project_ids: Optional[str] = Query(None, description="Comma-separated project IDs"),
    db: AsyncSession = Depends(get_db),
):
    """Get R&D health metrics for a time period.

    Args:
        start_date: Start date for calculation (default: 30 days ago)
        end_date: End date for calculation (default: today)
        employee_ids: Filter by specific employee IDs
        project_ids: Filter by specific project IDs
        db: Database session

    Returns:
        R&D health metrics with all calculated indicators
    """
    parsed_start = date.fromisoformat(start_date) if start_date else None
    parsed_end = date.fromisoformat(end_date) if end_date else None
    parsed_emp_ids = employee_ids.split(",") if employee_ids else None
    parsed_proj_ids = project_ids.split(",") if project_ids else None

    service = RnDHealthMetricsService(db)
    metrics = await service.calculate_health_metrics(
        start_date=parsed_start,
        end_date=parsed_end,
        employee_ids=parsed_emp_ids,
        project_ids=parsed_proj_ids,
    )

    return {
        "overall_health_score": round(metrics.overall_health_score, 2),
        "module_maturity_index": round(metrics.module_maturity_index, 2),
        "ontime_completion_rate": round(metrics.ontime_completion_rate, 2),
        "tech_debt_concentration": round(metrics.tech_debt_concentration, 2),
        "task_delay_rate": round(metrics.task_delay_rate, 2),
        "single_point_dependency_risk": round(metrics.single_point_dependency_risk, 2),
        "r_and_d_protection_time": round(metrics.r_and_d_protection_time, 2),
        "summary": {
            "tasks_completed": metrics.tasks_completed,
            "tasks_total": metrics.tasks_total,
            "tech_debt_tasks": metrics.tech_debt_tasks,
            "overdue_tasks": metrics.overdue_tasks,
            "single_point_dependencies": metrics.single_point_dependencies,
        },
        "top_modules": metrics.top_modules,
    }


@router.get("/rnd-health/trend")
async def get_rnd_health_trend(
    days: int = Query(30, description="Number of days to look back"),
    interval_days: int = Query(7, description="Interval for each data point"),
    db: AsyncSession = Depends(get_db),
):
    """Get R&D health score trend over time.

    Args:
        days: Number of days to look back
        interval_days: Interval for each data point
        db: Database session

    Returns:
        List of health score data points with timestamps
    """
    service = RnDHealthMetricsService(db)
    trend = await service.get_trend_data(days=days, interval_days=interval_days)

    return {"trend": trend}


@router.get("/delivery-health")
async def get_delivery_health_metrics(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    project_ids: Optional[str] = Query(None, description="Comma-separated project IDs"),
    db: AsyncSession = Depends(get_db),
):
    """Get delivery health metrics for a time period.

    Args:
        start_date: Start date for calculation (default: 30 days ago)
        end_date: End date for calculation (default: today)
        project_ids: Filter by specific project IDs
        db: Database session

    Returns:
        Delivery health metrics with all calculated indicators
    """
    parsed_start = date.fromisoformat(start_date) if start_date else None
    parsed_end = date.fromisoformat(end_date) if end_date else None
    parsed_proj_ids = project_ids.split(",") if project_ids else None

    service = DeliveryHealthMetricsService(db)
    metrics = await service.calculate_health_metrics(
        start_date=parsed_start,
        end_date=parsed_end,
        project_ids=parsed_proj_ids,
    )

    return {
        "overall_health_score": round(metrics.overall_health_score, 2),
        "delivery_on_time_rate": round(metrics.delivery_on_time_rate, 2),
        "version_success_rate": round(metrics.version_success_rate, 2),
        "customer_issue_rate": round(metrics.customer_issue_rate, 2),
        "implementation_rollback_risk": round(metrics.implementation_rollback_risk, 2),
        "summary": {
            "projects_on_time": metrics.projects_on_time,
            "projects_total": metrics.projects_total,
            "versions_success": metrics.versions_success,
            "versions_total": metrics.versions_total,
        },
    }


@router.get("/delivery-health/trend")
async def get_delivery_health_trend(
    days: int = Query(30, description="Number of days to look back"),
    interval_days: int = Query(7, description="Interval for each data point"),
    db: AsyncSession = Depends(get_db),
):
    """Get delivery health score trend over time.

    Args:
        days: Number of days to look back
        interval_days: Interval for each data point
        db: Database session

    Returns:
        List of health score data points with timestamps
    """
    service = DeliveryHealthMetricsService(db)
    trend = await service.get_trend_data(days=days, interval_days=interval_days)

    return {"trend": trend}
