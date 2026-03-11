"""Test delivery health metrics calculation - standalone version."""

import asyncio
import sys
from pathlib import Path
from datetime import date, datetime, timedelta

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import database directly
from src.database import database

# Import SQLAlchemy components
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.feishu_tasks import FeishuProject, FeishuTask


class SimpleDeliveryHealthTest:
    """Simple test for delivery health metrics."""

    def __init__(self, db_session: AsyncSession):
        self._db = db_session

    async def test_customer_issue_query(self):
        """Test the customer issue query with PostgreSQL JSON operator."""
        print("\n>>> Testing customer issue query...")

        start_date = (datetime.utcnow().date() - timedelta(days=30))
        end_date = datetime.utcnow().date()

        query = (
            select(func.count(FeishuTask.id))
            .where(FeishuTask.status == "done")
            .where(
                (FeishuTask.labels.op("?")("bug"))
                | (FeishuTask.labels.op("?")("issue"))
            )
            .where(FeishuTask.completed_at >= start_date)
            .where(FeishuTask.completed_at <= datetime.combine(end_date, datetime.max.time()))
        )

        try:
            result = await self._db.execute(query)
            count = result.scalar() or 0
            print(f"✅ Query executed successfully! Found {count} tasks with bug/issue labels")
            return True
        except Exception as e:
            print(f"❌ Query failed: {e}")
            return False

    async def test_project_query(self):
        """Test project on-time query."""
        print("\n>>> Testing project on-time query...")

        start_date = (datetime.utcnow().date() - timedelta(days=30))
        end_date = datetime.utcnow().date()

        query = (
            select(func.count(FeishuProject.id))
            .where(FeishuProject.status == "done")
            .where(FeishuProject.actual_end_date <= FeishuProject.end_date)
            .where(FeishuProject.actual_end_date >= start_date)
            .where(FeishuProject.actual_end_date <= datetime.combine(end_date, datetime.max.time()))
        )

        try:
            result = await self._db.execute(query)
            count = result.scalar() or 0
            print(f"✅ Query executed successfully! Found {count} on-time projects")
            return True
        except Exception as e:
            print(f"❌ Query failed: {e}")
            return False


async def main():
    """Main test function."""
    print("=" * 60)
    print("Testing Delivery Health Metrics - SQL Query Fix")
    print("=" * 60)

    database.initialize()

    async with database.session_factory() as session:
        try:
            tester = SimpleDeliveryHealthTest(session)

            # Test customer issue query (this was the problematic one)
            success1 = await tester.test_customer_issue_query()

            # Test project query
            success2 = await tester.test_project_query()

            print("\n" + "=" * 60)
            if success1 and success2:
                print("✅ All tests passed!")
                print("\nThe SQL query fix is working correctly.")
                print("PostgreSQL JSON operator '?' is being used instead of json_contains().")
            else:
                print("❌ Some tests failed!")
            print("=" * 60)

        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await session.close()


if __name__ == "__main__":
    asyncio.run(main())
