"""Test script for R&D Health Metrics and Report Generation."""

import asyncio
import json
import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database import database


async def test_rnd_health_metrics():
    """Test R&D health metrics calculation."""
    print("=" * 60)
    print("Testing R&D Health Metrics Calculation")
    print("=" * 60)

    database.initialize()

    try:
        from src.services.metrics.rnd_health import RnDHealthMetricsService

        async with database.session_factory() as db:
            service = RnDHealthMetricsService(db)
            metrics = await service.calculate_health_metrics()

            print("\n>>> R&D Health Metrics:")
            print(f"Overall Health Score: {metrics.overall_health_score:.2%}")
            print(f"Module Maturity Index: {metrics.module_maturity_index:.2%}")
            print(f"Ontime Completion Rate: {metrics.ontime_completion_rate:.2%}")
            print(f"Tech Debt Concentration: {metrics.tech_debt_concentration:.2%}")
            print(f"Task Delay Rate: {metrics.task_delay_rate:.2%}")
            print(f"Single Point Dependency Risk: {metrics.single_point_dependency_risk:.2%}")
            print(f"R&D Protection Time: {metrics.r_and_d_protection_time:.2%}")

            print(f"\nTasks: {metrics.tasks_completed}/{metrics.tasks_total} completed")
            print(f"Tech Debt Tasks: {metrics.tech_debt_tasks}")
            print(f"Overdue Tasks: {metrics.overdue_tasks}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


async def test_delivery_health_metrics():
    """Test Delivery health metrics calculation."""
    print("\n" + "=" * 60)
    print("Testing Delivery Health Metrics Calculation")
    print("=" * 60)

    try:
        from src.services.metrics.delivery_health import DeliveryHealthMetricsService

        async with database.session_factory() as db:
            service = DeliveryHealthMetricsService(db)
            metrics = await service.calculate_health_metrics()

            print("\n>>> Delivery Health Metrics:")
            print(f"Overall Health Score: {metrics.overall_health_score:.2%}")
            print(f"Delivery On-Time Rate: {metrics.delivery_on_time_rate:.2%}")
            print(f"Version Success Rate: {metrics.version_success_rate:.2%}")
            print(f"Customer Issue Rate: {metrics.customer_issue_rate:.2%}")
            print(f"Rollback Risk: {metrics.implementation_rollback_risk:.2%}")

            print(f"\nProjects: {metrics.projects_on_time}/{metrics.projects_total} on time")
            print(f"Versions: {metrics.versions_success}/{metrics.versions_total} successful")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


async def test_trend_data():
    """Test trend data calculation."""
    print("\n" + "=" * 60)
    print("Testing Trend Data Calculation")
    print("=" * 60)

    try:
        from src.services.metrics.rnd_health import RnDHealthMetricsService

        async with database.session_factory() as db:
            service = RnDHealthMetricsService(db)
            trend = await service.get_trend_data(days=14, interval_days=7)

            print("\n>>> R&D Health Trend (last 14 days):")
            for point in trend:
                print(f"  {point['date']}: Overall={point['overall_score']:.2%}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


async def test_weekly_report():
    """Test weekly report generation."""
    print("\n" + "=" * 60)
    print("Testing Weekly Report Generation")
    print("=" * 60)

    try:
        from src.services.report.report_generation import ReportGenerationService

        async with database.session_factory() as db:
            service = ReportGenerationService(db)
            report = await service.generate_weekly_report()

            print("\n>>> Weekly Report Generated:")
            print(f"Period: {report.period_start} - {report.period_end}")
            print(f"Overall Health: {report.overall_health:.2%}")
            print(f"\nKey Metrics:")
            for key, value in report.key_metrics.items():
                print(f"  - {key}: {value}")

            print(f"\nAchievements ({len(report.achievements)}):")
            for item in report.achievements[:3]:
                print(f"  + {item}")

            print(f"\nChallenges ({len(report.challenges)}):")
            for item in report.challenges[:3]:
                print(f"  ! {item}")

            print(f"\nRecommendations ({len(report.recommendations)}):")
            for item in report.recommendations[:3]:
                print(f"  * {item}")

            print(f"\n📊 Summary:")
            print(f"  Tasks: {report.tasks_completed} completed, {report.tasks_in_progress} in progress")
            print(f"  Projects: {report.projects_on_track} on track, {report.projects_at_risk} at risk")

            # Print markdown format
            print("\n" + "=" * 60)
            print("Markdown Report:")
            print("=" * 60)
            print(report.to_markdown())

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


async def main():
    """Run all tests."""
    print("\n>>> Starting Health Metrics and Report Tests...\n")

    await test_rnd_health_metrics()
    await test_delivery_health_metrics()
    await test_trend_data()
    await test_weekly_report()

    print("\n" + "=" * 60)
    print(">>> All Tests Completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
