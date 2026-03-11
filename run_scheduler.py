#!/usr/bin/env python3
"""Scheduler runner script.

Run this script to start the scheduled task scheduler.
Can be run standalone or managed by PM2/systemd.

Usage:
    python run_scheduler.py
    python run_scheduler.py --once  # Run tasks once and exit
"""

import argparse
import asyncio
import signal
import sys

import structlog

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

from src.tasks.intelligence_tasks import (
    TASK_REGISTRY,
    crawl_arxiv_task,
    crawl_github_task,
    crawl_hackernews_task,
    generate_daily_report_task,
    analyze_pending_items_task,
)
from src.tasks.scheduler import TaskScheduler

logger = structlog.get_logger()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="AI Intelligence Scheduler")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run all tasks once and exit (for testing)",
    )
    parser.add_argument(
        "--task",
        type=str,
        help="Run specific task by name",
    )
    args = parser.parse_args()

    # Run single task
    if args.task:
        if args.task not in TASK_REGISTRY:
            print(f"Unknown task: {args.task}")
            print(f"Available tasks: {', '.join(TASK_REGISTRY.keys())}")
            sys.exit(1)

        logger.info("running_single_task", task=args.task)
        task_func = TASK_REGISTRY[args.task]
        await task_func()
        return

    # Run all tasks once (for testing)
    if args.once:
        logger.info("running_all_tasks_once")

        tasks_to_run = [
            crawl_arxiv_task,
            crawl_github_task,
            crawl_hackernews_task,
            analyze_pending_items_task,
            generate_daily_report_task,
        ]

        for task_func in tasks_to_run:
            try:
                logger.info("running_task", task=task_func.__name__)
                await task_func()
            except Exception as e:
                logger.error("task_failed", task=task_func.__name__, error=str(e))

        logger.info("all_tasks_completed")
        return

    # Start scheduler
    scheduler = TaskScheduler()

    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info("shutdown_signal_received", signal=sig)
        asyncio.create_task(scheduler.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await scheduler.start()

        # Keep running
        while scheduler.running:
            await asyncio.sleep(1)

    except Exception as e:
        logger.error("scheduler_error", error=str(e))
        raise

    finally:
        await scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
