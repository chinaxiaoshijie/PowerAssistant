"""
一键数据同步脚本 - 初始化数据库并运行首次同步.

Usage:
    python run_sync.py
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.data_sync.scheduler import DataSyncScheduler, run_initialization
from src.database import database


async def main():
    """Run data initialization and sync."""
    print("=" * 70)
    print("  管理助手 - 数据同步工具")
    print("=" * 70)

    # Initialize database
    print("\n[1/4] 初始化数据库连接...")
    database.initialize()
    print("  [OK] 数据库连接成功")

    # Initialize crawler sources and sample data
    print("\n[2/4] 初始化爬虫配置和示例数据...")
    await run_initialization()
    print("  [OK] 配置已初始化")

    # Create scheduler and run syncs
    scheduler = DataSyncScheduler()

    # GitHub crawl
    print("\n[3/4] 从 GitHub 抓取 AI 项目数据...")
    try:
        items = await scheduler.crawl_github(limit=10)
        print(f"  [OK] 成功抓取 {len(items)} 条 GitHub 数据")
        for item in items[:3]:
            print(f"    - {item.title[:50]}...")
    except Exception as e:
        print(f"  [FAIL] GitHub 抓取失败：{e}")
        print("  ! 将使用示例数据")

    # Feishu sync
    print("\n[4/4] 同步飞书通讯录...")
    try:
        stats = await scheduler.sync_feishu_organization()
        print(f"  [OK] 飞书同步完成:")
        print(f"    - 部门：{stats.get('departments', 0)} 个")
        print(f"    - 员工：{stats.get('employees', 0)} 人")
    except Exception as e:
        print(f"  [FAIL] 飞书同步失败：{e}")
        print("  ! 请检查飞书配置 (.env 中的 FEISHU_APP_ID 和 FEISHU_APP_SECRET)")

    print("\n" + "=" * 70)
    print("  同步完成！")
    print("=" * 70)
    print("\n  请刷新 Dashboard 查看数据:")
    print("  http://localhost:8000/dashboard")
    print("\n  API 文档:")
    print("  http://localhost:8000/api/docs")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n操作已取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n[FAIL] 错误：{e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
