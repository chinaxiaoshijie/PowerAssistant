"""Health check API routes."""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, get_feishu_client
from src.services.feishu.client import FeishuClient

logger = structlog.get_logger()
router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Basic health check endpoint.

    Verifies database connectivity.

    Returns:
        Health status with component checks
    """
    logger.debug("health_check_requested")

    checks = {
        "database": False,
        "feishu": False,
    }

    # Check database
    try:
        result = await db.execute(text("SELECT 1"))
        await result.scalar()
        checks["database"] = True
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))

    # Check Feishu connectivity (lightweight - just token check)
    # This is done in a separate endpoint to avoid blocking

    all_healthy = all(checks.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        "checks": checks,
    }


@router.get("/feishu")
async def feishu_health_check(
    client: FeishuClient = Depends(get_feishu_client),
):
    """Feishu API connectivity check.

    Verifies Feishu API token acquisition.

    Returns:
        Feishu connection status
    """
    logger.debug("feishu_health_check_requested")

    try:
        # Try to get token (this validates credentials)
        # We access the internal method to trigger token acquisition
        await client._get_access_token()

        return {
            "status": "healthy",
            "message": "Feishu API connection successful",
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("feishu_health_check_failed", error=str(e))
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "message": f"Feishu API connection failed: {str(e)}",
                "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            },
        )
