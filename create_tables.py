"""Create Feishu tasks and projects tables."""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database import database
from src.models.feishu_tasks import FeishuTask, FeishuProject, FeishuOKR
from src.models.organization import Department, Employee
from src.models.sync_log import SyncLog
from src.models.document import FeishuDocument
from src.models.ai_intelligence import (
    CrawlerSource,
    IntelligenceItem,
    IntelligenceAnalysis,
    IntelligenceReport,
)
from sqlalchemy import text


async def create_tables():
    """Create all tables in the database."""
    print(">>> Creating database tables...")

    database.initialize()

    async with database.engine.begin() as conn:
        # Create tables
        await conn.run_sync(FeishuTask.metadata.create_all, bind=conn)
        print(">>> Created feishu_tasks table")

        await conn.run_sync(FeishuProject.metadata.create_all, bind=conn)
        print(">>> Created feishu_projects table")

        await conn.run_sync(FeishuOKR.metadata.create_all, bind=conn)
        print(">>> Created feishu_okrs table")

    print("\n>>> All tables created successfully!")


async def check_existing_tables():
    """Check which tables already exist."""
    print(">>> Checking existing tables...")

    database.initialize()

    async with database.session_factory() as session:
        result = await session.execute(
            text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
            )
        )
        tables = result.fetchall()
        print(f">>> Existing tables: {[t[0] for t in tables]}")


if __name__ == "__main__":
    asyncio.run(check_existing_tables())
    asyncio.run(create_tables())
