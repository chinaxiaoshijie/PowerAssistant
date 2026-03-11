"""Test delivery health metrics calculation."""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.services.metrics.delivery_health import DeliveryHealthMetricsService
from src.database import database


async def test_delivery_health():
    """Test delivery health metrics."""
    print("=" * 60)
    print("Testing Delivery Health Metrics")
    print("=" * 60)

    database.initialize()

    async with database.session_factory() as session:
        try:
            service = DeliveryHealthMetricsService(session)
            metrics = await service.calculate_health_metrics()

            print("\n✅ Delivery Health Metrics:")
            print(f"Overall Health Score: {metrics.overall_health_score:.2%}")
            print(f"Delivery On-Time Rate: {metrics.delivery_on_time_rate:.2%}")
            print(f"Version Success Rate: {metrics.version_success_rate:.2%}")
            print(f"Customer Issue Rate: {metrics.customer_issue_rate:.2%}")
            print(f"Rollback Risk: {metrics.implementation_rollback_risk:.2%}")
            print(f"\nProjects: {metrics.projects_on_time}/{metrics.projects_total} on-time")
            print(f"Versions: {metrics.versions_success}/{metrics.versions_total} successful")

            print("\n✅ Test passed!")

        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await session.close()


if __name__ == "__main__":
    asyncio.run(test_delivery_health())
