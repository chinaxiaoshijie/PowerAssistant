"""Create Feishu tasks and projects tables."""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database import database
from sqlalchemy import text


async def create_feishu_task_tables():
    """Create feishu tasks and projects tables manually."""
    print(">>> Creating feishu task tables...")

    database.initialize()

    async with database.session_factory() as session:
        try:
            # Check if tables exist
            result = await session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('feishu_tasks', 'feishu_projects', 'feishu_okrs')"
                )
            )
            existing_tables = {row[0] for row in result.fetchall()}
            print(f">>> Existing task tables: {existing_tables}")

            # Create feishu_tasks table if not exists
            if "feishu_tasks" not in existing_tables:
                await session.execute(
                    text(
                        """
                    CREATE TABLE feishu_tasks (
                        id SERIAL PRIMARY KEY,
                        feishu_task_id VARCHAR(100) UNIQUE NOT NULL,
                        title VARCHAR(500) NOT NULL,
                        description TEXT,
                        status VARCHAR(50) NOT NULL DEFAULT 'pending',
                        priority VARCHAR(20) NOT NULL DEFAULT 'p2',
                        due_date DATE,
                        completed_at TIMESTAMP,
                        assignee_ids JSON NOT NULL DEFAULT '[]',
                        reporter_id VARCHAR(100),
                        project_id VARCHAR(100),
                        parent_task_id VARCHAR(100),
                        labels JSON NOT NULL DEFAULT '[]',
                        is_tech_debt BOOLEAN NOT NULL DEFAULT FALSE,
                        story_points FLOAT,
                        actual_hours FLOAT,
                        estimated_hours FLOAT,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        sync_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE INDEX ix_feishu_tasks_status ON feishu_tasks(status);
                    CREATE INDEX ix_feishu_tasks_priority ON feishu_tasks(priority);
                    CREATE INDEX ix_feishu_tasks_due_date ON feishu_tasks(due_date);
                    CREATE INDEX ix_feishu_tasks_project ON feishu_tasks(project_id);
                    """
                    )
                )
                print(">>> Created feishu_tasks table")
            else:
                print(">>> feishu_tasks table already exists")

            # Create feishu_projects table if not exists
            if "feishu_projects" not in existing_tables:
                await session.execute(
                    text(
                        """
                    CREATE TABLE feishu_projects (
                        id SERIAL PRIMARY KEY,
                        feishu_project_id VARCHAR(100) UNIQUE NOT NULL,
                        name VARCHAR(200) NOT NULL,
                        description TEXT,
                        status VARCHAR(50) NOT NULL DEFAULT 'planning',
                        start_date DATE,
                        end_date DATE,
                        actual_end_date DATE,
                        owner_id VARCHAR(100),
                        member_ids JSON NOT NULL DEFAULT '[]',
                        milestones JSON NOT NULL DEFAULT '[]',
                        risk_level VARCHAR(20) NOT NULL DEFAULT 'low',
                        progress INTEGER NOT NULL DEFAULT 0,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        sync_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE INDEX ix_feishu_projects_status ON feishu_projects(status);
                    CREATE INDEX ix_feishu_projects_risk ON feishu_projects(risk_level);
                    """
                    )
                )
                print(">>> Created feishu_projects table")
            else:
                print(">>> feishu_projects table already exists")

            # Create feishu_okrs table if not exists
            if "feishu_okrs" not in existing_tables:
                await session.execute(
                    text(
                        """
                    CREATE TABLE feishu_okrs (
                        id SERIAL PRIMARY KEY,
                        feishu_okr_id VARCHAR(100) UNIQUE NOT NULL,
                        objective VARCHAR(500) NOT NULL,
                        key_results JSON NOT NULL DEFAULT '[]',
                        progress INTEGER NOT NULL DEFAULT 0,
                        owner_id VARCHAR(100),
                        cycle VARCHAR(50) NOT NULL,
                        parent_okr_id VARCHAR(100),
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        sync_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE INDEX ix_feishu_okrs_cycle ON feishu_okrs(cycle);
                    CREATE INDEX ix_feishu_okrs_owner ON feishu_okrs(owner_id);
                    """
                    )
                )
                print(">>> Created feishu_okrs table")
            else:
                print(">>> feishu_okrs table already exists")

            await session.commit()
            print("\n>>> All task tables created successfully!")

        except Exception as e:
            print(f">>> Error creating tables: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(create_feishu_task_tables())
