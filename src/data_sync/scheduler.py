"""数据同步调度服务 - 自动抓取和同步所有数据源.

该模块提供:
1. 定时抓取 AI 情报 (GitHub/arXiv/HackerNews)
2. 定时同步飞书数据 (组织架构、任务、项目)
3. 数据持久化到 PostgreSQL
4. 可配置的调度策略
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import database
from src.models.ai_intelligence import CrawlerSource, IntelligenceItem
from src.models.organization import Department, Employee
from src.services.ai_intelligence import IntelligenceGatheringService
from src.services.feishu.client import FeishuClient
from src.services.feishu.org_sync import OrganizationSyncService

logger = structlog.get_logger()


class DataSyncScheduler:
    """数据同步调度器 - 管理所有数据源的自动同步.

    Usage:
        scheduler = DataSyncScheduler()
        await scheduler.start()
        # 运行一段时间后
        await scheduler.stop()
    """

    def __init__(self):
        """Initialize scheduler."""
        self._running = False
        self._tasks = []
        self._logger = logger.bind(component="DataSyncScheduler")

    async def start(self):
        """Start all scheduled sync tasks."""
        self._running = True
        self._logger.info("starting_scheduler")

        # Initialize database
        database.initialize()

        # Start background tasks
        self._tasks = [
            asyncio.create_task(self._github_crawl_loop()),
            asyncio.create_task(self._arxiv_crawl_loop()),
            asyncio.create_task(self._feishu_org_sync_loop()),
            asyncio.create_task(self._daily_report_loop()),
        ]

        self._logger.info("scheduler_started", task_count=len(self._tasks))

    async def stop(self):
        """Stop all scheduled tasks."""
        self._running = False
        self._logger.info("stopping_scheduler")

        for task in self._tasks:
            task.cancel()

        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._logger.info("scheduler_stopped")

    async def _github_crawl_loop(self):
        """Background loop for GitHub crawling (every 12 hours)."""
        while self._running:
            try:
                await self.crawl_github()
                # Wait 12 hours
                await asyncio.sleep(12 * 3600)
            except Exception as e:
                self._logger.error("github_crawl_loop_error", error=str(e))
                await asyncio.sleep(300)  # Retry after 5 minutes on error

    async def _arxiv_crawl_loop(self):
        """Background loop for arXiv crawling (every 6 hours)."""
        while self._running:
            try:
                await self.crawl_arxiv()
                # Wait 6 hours
                await asyncio.sleep(6 * 3600)
            except Exception as e:
                self._logger.error("arxiv_crawl_loop_error", error=str(e))
                await asyncio.sleep(300)

    async def _feishu_org_sync_loop(self):
        """Background loop for Feishu org sync (every 1 hour)."""
        while self._running:
            try:
                await self.sync_feishu_organization()
                # Wait 1 hour
                await asyncio.sleep(3600)
            except Exception as e:
                self._logger.error("feishu_sync_loop_error", error=str(e))
                await asyncio.sleep(300)

    async def _daily_report_loop(self):
        """Background loop for daily report generation (once per day at 9 AM)."""
        while self._running:
            try:
                # Calculate time until next 9 AM
                now = datetime.now()
                next_9am = now.replace(hour=9, minute=0, second=0, microsecond=0)
                if next_9am <= now:
                    next_9am += timedelta(days=1)

                wait_seconds = (next_9am - now).total_seconds()
                self._logger.info("waiting_for_daily_report", wait_hours=wait_seconds/3600)

                await asyncio.sleep(wait_seconds)
                await self.generate_daily_report()
            except Exception as e:
                self._logger.error("daily_report_loop_error", error=str(e))
                await asyncio.sleep(300)

    async def crawl_github(self, limit: int = 20) -> list[IntelligenceItem]:
        """Crawl GitHub trending AI repositories.

        Args:
            limit: Maximum number of items to fetch

        Returns:
            List of crawled and stored items
        """
        self._logger.info("starting_github_crawl", limit=limit)

        async with database.session_factory() as db:
            service = IntelligenceGatheringService(db)
            items = await service.crawl_and_store("github", limit=limit)
            self._logger.info(
                "github_crawl_complete",
                items_crawled=len(items),
            )
            return items

    async def crawl_arxiv(self, limit: int = 20) -> list[IntelligenceItem]:
        """Crawl arXiv AI papers.

        Args:
            limit: Maximum number of items to fetch

        Returns:
            List of crawled and stored items
        """
        self._logger.info("starting_arxiv_crawl", limit=limit)

        async with database.session_factory() as db:
            service = IntelligenceGatheringService(db)
            items = await service.crawl_and_store("arxiv", limit=limit)
            self._logger.info(
                "arxiv_crawl_complete",
                items_crawled=len(items),
            )
            return items

    async def sync_feishu_organization(self) -> dict:
        """Sync Feishu organization data (departments and employees).

        Returns:
            Sync statistics
        """
        self._logger.info("starting_feishu_sync")

        stats = {"departments": 0, "employees": 0, "errors": []}

        async with FeishuClient() as client:
            async with database.session_factory() as db:
                sync_service = OrganizationSyncService(client, db)

                try:
                    # Use full_sync method which syncs both departments and employees
                    sync_log = await sync_service.full_sync()
                    stats["departments"] = sync_log.records_created + sync_log.records_updated
                    stats["employees"] = sync_log.records_created + sync_log.records_updated
                    self._logger.info(
                        "feishu_sync_complete",
                        stats=stats,
                    )

                except Exception as e:
                    stats["errors"].append(str(e))
                    self._logger.error("feishu_sync_error", error=str(e))
                    raise

        return stats

    async def generate_daily_report(self) -> Optional[IntelligenceItem]:
        """Generate daily intelligence report.

        Returns:
            Generated report or None if no data
        """
        self._logger.info("starting_daily_report_generation")

        async with database.session_factory() as db:
            service = IntelligenceGatheringService(db)
            report = await service.generate_daily_report()
            if report:
                self._logger.info(
                    "daily_report_generated",
                    report_id=report.id,
                    title=report.title,
                )
            return report


class DataInitializer:
    """数据初始化器 - 首次运行时填充示例数据."""

    def __init__(self):
        self._logger = logger.bind(component="DataInitializer")

    async def initialize(self):
        """Initialize database with sample and config data."""
        self._logger.info("starting_initialization")

        database.initialize()

        async with database.session_factory() as db:
            # Initialize crawler sources
            await self._init_crawler_sources(db)

            # Initialize sample data if empty
            await self._init_sample_data(db)

        self._logger.info("initialization_complete")

    async def _init_crawler_sources(self, db: AsyncSession):
        """Initialize crawler source configurations."""
        from src.models.ai_intelligence import CrawlerSource

        sources = [
            CrawlerSource(
                name="GitHub Trending AI",
                source_type="github",
                url="https://api.github.com/search/repositories",
                config={
                    "query": "AI education machine-learning stars:>100",
                    "sort": "updated",
                    "order": "desc",
                },
                fetch_interval_hours=12,
                is_active=True,
            ),
            CrawlerSource(
                name="arXiv AI Papers",
                source_type="arxiv",
                url="http://export.arxiv.org/api/query",
                config={
                    "categories": ["cs.AI", "cs.CL", "cs.LG", "cs.CV"],
                    "max_results": 50,
                },
                fetch_interval_hours=6,
                is_active=True,
            ),
            CrawlerSource(
                name="Hacker News AI",
                source_type="hackernews",
                url="https://hacker-news.firebaseio.com/v0",
                config={
                    "keywords": ["AI", "machine learning", "education", "LLM"],
                },
                fetch_interval_hours=2,
                is_active=True,
            ),
        ]

        for source in sources:
            # Check if source already exists
            result = await db.execute(
                select(CrawlerSource).where(
                    CrawlerSource.source_type == source.source_type
                )
            )
            if not result.scalar_one_or_none():
                db.add(source)
                self._logger.info(
                    "added_crawler_source",
                    source_type=source.source_type,
                )

        await db.commit()

    async def _init_sample_data(self, db: AsyncSession):
        """Initialize sample intelligence items if database is empty."""
        # Check if data exists
        result = await db.execute(select(IntelligenceItem).limit(1))
        if result.scalar_one_or_none():
            self._logger.info("sample_data_already_exists")
            return

        from datetime import datetime, timedelta

        items = [
            IntelligenceItem(
                source_type="github",
                source_name="GitHub",
                external_id="github_langchain",
                title="LangChain: Build context-aware reasoning applications",
                url="https://github.com/langchain-ai/langchain",
                content="LangChain is a framework for developing applications powered by language models.",
                content_hash="hash1",
                author="LangChain Team",
                published_at=datetime.utcnow(),
                language="en",
                category="development_tool",
                summary="开源LLM应用开发框架，支持多种模型和工具集成",
                key_points=["支持多种LLM", "模块化设计", "丰富的集成", "社区活跃"],
                relevance_score=0.88,
                relevance_reasoning="可用于构建我们的AI助教系统，提供对话和工具调用能力",
                tags=["LLM", "Framework", "Open Source", "Python"],
                technologies=["Python", "TypeScript", "OpenAI"],
                is_processed=True,
                is_read=False,
                is_notified=False,
            ),
            IntelligenceItem(
                source_type="github",
                source_name="GitHub",
                external_id="github_transformers",
                title="Transformers: State-of-the-art ML for PyTorch",
                url="https://github.com/huggingface/transformers",
                content="Transformers provides thousands of pretrained models for NLP, vision, audio.",
                content_hash="hash2",
                author="Hugging Face",
                published_at=datetime.utcnow() - timedelta(hours=5),
                language="en",
                category="algorithm",
                summary="Hugging Face的Transformers库，提供预训练模型和训练工具",
                key_points=["预训练模型库", "支持NLP/CV/音频", "易于微调", "社区活跃"],
                relevance_score=0.92,
                relevance_reasoning="我们的NLP模块可以直接使用这些预训练模型，快速构建功能",
                tags=["NLP", "Transformers", "PyTorch", "Deep Learning"],
                technologies=["PyTorch", "Python", "CUDA"],
                is_processed=True,
                is_read=True,
                is_notified=False,
            ),
            IntelligenceItem(
                source_type="arxiv",
                source_name="arXiv",
                external_id="arxiv_2403_edu",
                title="Large Language Models for Educational Assessment: A Survey",
                url="https://arxiv.org/abs/2403.12345",
                content="This paper surveys LLM applications in educational assessment.",
                content_hash="hash3",
                author="Education AI Research Group",
                published_at=datetime.utcnow() - timedelta(days=1),
                language="en",
                category="research_paper",
                summary="大语言模型在教育评估中的应用综述，提出新的评估框架",
                key_points=["教育评估框架", "自动评分", "个性化反馈", "多语言支持"],
                relevance_score=0.95,
                relevance_reasoning="直接相关！可以用于改进我们的实验评估和作业批改功能",
                tags=["LLM", "Education", "Assessment", "Survey"],
                technologies=["PyTorch", "BERT", "GPT"],
                is_processed=True,
                is_read=False,
                is_notified=False,
            ),
            IntelligenceItem(
                source_type="github",
                source_name="GitHub",
                external_id="github_openedu",
                title="OpenEduAI: Open Source Education AI Platform",
                url="https://github.com/example/openedu-ai",
                content="An open-source AI platform for education with personalized learning.",
                content_hash="hash4",
                author="OpenEdu Team",
                published_at=datetime.utcnow() - timedelta(hours=12),
                language="en",
                category="product",
                summary="开源AI教育平台，支持个性化学习路径和实时反馈",
                key_points=["个性化学习", "实时反馈", "学习分析", "开源免费"],
                relevance_score=0.85,
                relevance_reasoning="竞品分析参考，可以借鉴其个性化学习功能设计",
                tags=["Education", "AI", "Platform", "Open Source"],
                technologies=["Python", "React", "PostgreSQL"],
                is_processed=True,
                is_read=False,
                is_notified=False,
            ),
        ]

        for item in items:
            db.add(item)

        await db.commit()
        self._logger.info("added_sample_items", count=len(items))


# Global scheduler instance
_sync_scheduler: Optional[DataSyncScheduler] = None


async def start_scheduler():
    """Start the global data sync scheduler."""
    global _sync_scheduler
    if _sync_scheduler is None:
        _sync_scheduler = DataSyncScheduler()
        await _sync_scheduler.start()


async def stop_scheduler():
    """Stop the global data sync scheduler."""
    global _sync_scheduler
    if _sync_scheduler:
        await _sync_scheduler.stop()
        _sync_scheduler = None


async def run_initialization():
    """Run database initialization."""
    initializer = DataInitializer()
    await initializer.initialize()


async def run_single_sync():
    """Run a single sync cycle (for testing)."""
    scheduler = DataSyncScheduler()

    # Initialize
    await run_initialization()

    # Run syncs
    logger.info("running_single_sync_cycle")

    try:
        # GitHub crawl
        github_items = await scheduler.crawl_github(limit=10)
        logger.info("single_sync_github_complete", items=len(github_items))

        # Feishu sync
        feishu_stats = await scheduler.sync_feishu_organization()
        logger.info("single_sync_feishu_complete", stats=feishu_stats)

    except Exception as e:
        logger.error("single_sync_error", error=str(e))
        raise


if __name__ == "__main__":
    # Run initialization and single sync
    asyncio.run(run_initialization())
    print("Database initialized with sample data!")
    print("Start the scheduler with: python -c 'from src.data_sync.scheduler import start_scheduler; import asyncio; asyncio.run(start_scheduler())'")
