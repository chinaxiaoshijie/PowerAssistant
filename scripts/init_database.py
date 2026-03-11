"""
初始化数据库数据脚本 - 一键填充示例数据.

Usage:
    python scripts/init_database.py
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data_sync.scheduler import run_initialization, run_single_sync
from src.database import database


async def main():
    """Initialize database with sample data."""
    print("=" * 60)
    print("管理助手 - 数据库数据初始化")
    print("=" * 60)

    try:
        # Initialize database connection
        print("\n[1/3] 连接数据库...")
        database.initialize()
        print("✓ 数据库连接成功")

        # Run initialization
        print("\n[2/3] 初始化爬虫配置...")
        await run_initialization()
        print("✓ 爬虫配置已初始化")

        # Run single sync to fetch real data
        print("\n[3/3] 抓取示例数据...")
        from src.data_sync.scheduler import DataSyncScheduler

        scheduler = DataSyncScheduler()

        # Try to fetch real GitHub data
        try:
            items = await scheduler.crawl_github(limit=5)
            print(f"✓ 从 GitHub 抓取了 {len(items)} 条数据")
        except Exception as e:
            print(f"! GitHub 抓取失败 (使用示例数据): {e}")

        # Try to sync Feishu
        try:
            stats = await scheduler.sync_feishu_organization()
            print(f"✓ 飞书通讯录同步完成:")
            print(f"  - 部门: {stats.get('departments', 0)} 个")
            print(f"  - 员工: {stats.get('employees', 0)} 人")
        except Exception as e:
            print(f"! 飞书同步失败: {e}")

        print("\n" + "=" * 60)
        print("初始化完成！请刷新 Dashboard 查看数据")
        print("=" * 60)
        print("\n访问 http://localhost:8000/dashboard 查看结果")

    except Exception as e:
        print(f"\n✗ 初始化失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
