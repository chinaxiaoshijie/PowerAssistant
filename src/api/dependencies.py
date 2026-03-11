"""FastAPI dependencies for dependency injection."""

from typing import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.database import get_db_session
from src.services.feishu.client import FeishuClient

logger = structlog.get_logger()


# Alias for cleaner imports
get_db = get_db_session


async def get_feishu_client() -> AsyncGenerator[FeishuClient, None]:
    """Get Feishu client dependency.

    Yields:
        FeishuClient: Configured Feishu API client

    Example:
        >>> @app.get("/departments")
        ... async def get_depts(client: FeishuClient = Depends(get_feishu_client)):
        ...     ...
    """
    async with FeishuClient() as client:
        yield client
