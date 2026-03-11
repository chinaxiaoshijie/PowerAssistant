"""Main AI Intelligence Gathering Service.

Orchestrates crawling, analysis, and reporting of AI intelligence.
"""

from datetime import datetime, timedelta
from typing import AsyncGenerator, List, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.ai_intelligence import (
    CrawlerSource,
    IntelligenceAnalysis,
    IntelligenceItem,
    IntelligenceReport,
)
from src.services.ai_intelligence.analyzer import ContentAnalyzer
from src.services.ai_intelligence.base import BaseCrawler, CrawlResult
from src.services.ai_intelligence.crawlers.arxiv import ArxivCrawler
from src.services.ai_intelligence.crawlers.github import GitHubTrendingCrawler
from src.services.ai_intelligence.crawlers.hackernews import HackerNewsCrawler
from src.services.ai_intelligence.crawlers.reddit import RedditCrawler
from src.services.ai_intelligence.crawlers.rss import RSSCrawler

logger = structlog.get_logger()


class IntelligenceGatheringService:
    """Main service for AI intelligence gathering.

    Coordinates:
    - Crawling from multiple sources
    - Content analysis with AI
    - Database storage
    - Report generation
    """

    # Registry of available crawlers
    CRAWLERS = {
        "arxiv": ArxivCrawler,
        "github": GitHubTrendingCrawler,
        "hackernews": HackerNewsCrawler,
        "reddit": RedditCrawler,
        "rss": RSSCrawler,
    }

    def __init__(self, db_session: AsyncSession):
        """Initialize service.

        Args:
            db_session: Database session
        """
        self._db = db_session
        self._logger = logger.bind(component="IntelligenceGatheringService")
        self._analyzer = ContentAnalyzer()

    async def crawl_and_store(
        self,
        source_type: str,
        since: Optional[datetime] = None,
        limit: int = 50,
        auto_analyze: bool = True,
    ) -> List[IntelligenceItem]:
        """Crawl from a source and store results.

        Args:
            source_type: Type of source (arxiv/github/hackernews)
            since: Only fetch items newer than this
            limit: Maximum items to fetch
            auto_analyze: Whether to analyze items immediately

        Returns:
            List of stored intelligence items
        """
        self._logger.info(
            "starting_crawl",
            source=source_type,
            since=since,
            limit=limit,
        )

        # Get crawler class
        crawler_class = self.CRAWLERS.get(source_type)
        if not crawler_class:
            raise ValueError(f"Unknown source type: {source_type}")

        # Create crawler instance
        crawler = crawler_class()
        items: List[IntelligenceItem] = []

        try:
            async for result in crawler.crawl(since=since, limit=limit):
                # Check for duplicates
                content_hash = result.compute_hash()

                existing = await self._db.execute(
                    select(IntelligenceItem).where(
                        IntelligenceItem.content_hash == content_hash
                    )
                )
                if existing.scalar_one_or_none():
                    self._logger.debug("duplicate_item_skipped", title=result.title[:50])
                    continue

                # Create item
                item = IntelligenceItem(
                    source_type=crawler.get_source_type(),
                    source_name=crawler.get_source_name(),
                    external_id=result.external_id,
                    title=result.title,
                    url=result.url,
                    content=result.content,
                    content_hash=content_hash,
                    author=result.author,
                    published_at=result.published_at,
                    metadata=result.metadata,
                )

                self._db.add(item)
                await self._db.flush()  # Get ID

                items.append(item)

                # Auto-analyze if enabled
                if auto_analyze:
                    await self._analyze_item(item)

                self._logger.debug("item_stored", id=item.id, title=item.title[:50])

            await self._db.commit()

            self._logger.info(
                "crawl_completed",
                source=source_type,
                items_stored=len(items),
            )

            return items

        except Exception as e:
            await self._db.rollback()
            self._logger.error("crawl_failed", source=source_type, error=str(e))
            raise

        finally:
            await crawler.close()

    async def _analyze_item(self, item: IntelligenceItem) -> IntelligenceAnalysis:
        """Analyze a single item.

        Args:
            item: Item to analyze

        Returns:
            Analysis result
        """
        self._logger.debug("analyzing_item", id=item.id, title=item.title[:50])

        # Convert to crawl result for analyzer
        result = CrawlResult(
            title=item.title,
            url=item.url,
            content=item.content,
            author=item.author,
            published_at=item.published_at,
            external_id=item.external_id,
            metadata=item.metadata,
        )

        # Run analysis
        analysis_data = await self._analyzer.analyze(result)

        # Update item
        item.category = analysis_data.get("category", "uncategorized")
        item.summary = analysis_data.get("summary")
        item.key_points = analysis_data.get("key_points", [])
        item.tags = analysis_data.get("tags", [])
        item.technologies = analysis_data.get("technologies", [])
        item.relevance_score = analysis_data.get("relevance_score", 0)
        item.relevance_reasoning = analysis_data.get("relevance_reasoning")
        item.is_processed = True

        # Create analysis record
        analysis = IntelligenceAnalysis(
            intelligence_item_id=item.id,
            analysis_type="general",
            model_used="qwen-max",  # TODO: Get from ai_engine
            analysis_content=analysis_data.get("relevance_reasoning", ""),
            action_items=analysis_data.get("action_items", []),
            applicability_score=analysis_data.get("relevance_score", 0),
        )

        self._db.add(analysis)

        self._logger.debug(
            "item_analyzed",
            id=item.id,
            category=item.category,
            relevance=item.relevance_score,
        )

        return analysis

    async def analyze_pending_items(
        self,
        batch_size: int = 10,
        min_relevance: float = 0.0,
    ) -> int:
        """Analyze unprocessed items.

        Args:
            batch_size: Number of items to analyze
            min_relevance: Minimum relevance to process

        Returns:
            Number of items analyzed
        """
        self._logger.info("analyzing_pending_items", batch_size=batch_size)

        # Get unprocessed items
        result = await self._db.execute(
            select(IntelligenceItem)
            .where(IntelligenceItem.is_processed == False)
            .limit(batch_size)
        )
        items = result.scalars().all()

        count = 0
        for item in items:
            try:
                await self._analyze_item(item)
                count += 1

                # Skip low relevance items if threshold set
                if min_relevance > 0 and item.relevance_score < min_relevance:
                    self._logger.debug(
                        "low_relevance_skipped",
                        id=item.id,
                        score=item.relevance_score,
                    )

            except Exception as e:
                self._logger.error(
                    "item_analysis_failed",
                    id=item.id,
                    error=str(e),
                )

        await self._db.commit()

        self._logger.info("analysis_completed", items_analyzed=count)
        return count

    async def generate_daily_report(self) -> IntelligenceReport:
        """Generate daily intelligence report.

        Returns:
            Generated report
        """
        yesterday = datetime.utcnow() - timedelta(days=1)

        # Get items from last 24 hours
        result = await self._db.execute(
            select(IntelligenceItem)
            .where(IntelligenceItem.created_at >= yesterday)
            .where(IntelligenceItem.is_processed == True)
            .order_by(IntelligenceItem.relevance_score.desc())
        )
        items = result.scalars().all()

        self._logger.info("generating_daily_report", items_count=len(items))

        # Categorize items
        category_counts = {}
        for item in items:
            cat = item.category
            category_counts[cat] = category_counts.get(cat, 0) + 1

        # Build highlights
        highlights = []
        for item in items[:10]:  # Top 10
            highlights.append({
                "id": item.id,
                "title": item.title,
                "url": item.url,
                "category": item.category,
                "relevance_score": item.relevance_score,
                "summary": item.summary,
            })

        # Create report
        report = IntelligenceReport(
            report_type="daily",
            title=f"AI Intelligence Daily Report - {datetime.utcnow().strftime('%Y-%m-%d')}",
            period_start=yesterday,
            period_end=datetime.utcnow(),
            summary=f"Collected {len(items)} AI intelligence items in the last 24 hours.",
            highlights=highlights,
            category_breakdown=category_counts,
        )

        self._db.add(report)
        await self._db.commit()

        self._logger.info("daily_report_generated", id=report.id, items=len(items))

        return report

    async def get_high_relevance_items(
        self,
        threshold: float = 0.7,
        limit: int = 20,
    ) -> List[IntelligenceItem]:
        """Get high relevance items.

        Args:
            threshold: Minimum relevance score
            limit: Maximum items

        Returns:
            List of high relevance items
        """
        result = await self._db.execute(
            select(IntelligenceItem)
            .where(IntelligenceItem.relevance_score >= threshold)
            .where(IntelligenceItem.is_processed == True)
            .order_by(IntelligenceItem.relevance_score.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
