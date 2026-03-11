"""
启动数据同步调度器 - 后台自动抓取和同步.

Usage:
    python scripts/start_scheduler.py
    # 按 Ctrl+C 停止
"""

import asyncio
import signal
import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data_sync.scheduler import start_scheduler, stop_scheduler
from src.database import database


async def main():
    """Start the data sync scheduler."""
    print("=" * 60)
    print("管理助手 - 数据同步调度器")
    print("=" * 60)

    # Setup signal handlers
    loop = asyncio.get_event_loop()

    def signal_handler(sig, frame):
        print("\n\n接收到停止信号，正在关闭...")
        asyncio.create_task(stop_scheduler())
        loop.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Initialize database
        print("\n[1/2] 初始化数据库...")
        database.initialize()
        print("✓ 数据库连接成功")

        # Start scheduler
        print("\n[2/2] 启动调度器...")
        print("\n定时任务:")
        print("  - GitHub 抓取: 每 12 小时")
        print("  - arXiv 抓取: 每 6 小时")
        print("  - 飞书同步: 每 1 小时")
        print("  - 日报生成: 每天 9:00")
        print("\n" + "=" * 60)

        await start_scheduler()

        print("调度器运行中... 按 Ctrl+C 停止\n")

        # Keep running
        while True:
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        print("\n调度器已停止")
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n已退出")
        sys.exit(0)
