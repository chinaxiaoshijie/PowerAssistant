"""AI Intelligence Gathering Module.

This module provides automated intelligence gathering from AI-related sources:
- arXiv papers
- GitHub trending repositories
- Hacker News
- RSS feeds

Example usage:
    >>> from src.services.ai_intelligence import IntelligenceGatheringService
    >>> service = IntelligenceGatheringService(db_session)
    >>>
    >>> # Crawl from a source
    >>> items = await service.crawl_and_store("arxiv", limit=50)
    >>>
    >>> # Analyze pending items
    >>> await service.analyze_pending_items(batch_size=10)
    >>>
    >>> # Generate report
    >>> report = await service.generate_daily_report()
"""

from src.services.ai_intelligence.analyzer import ContentAnalyzer
from src.services.ai_intelligence.base import BaseCrawler, CrawlResult
from src.services.ai_intelligence.service import IntelligenceGatheringService

__all__ = [
    "BaseCrawler",
    "CrawlResult",
    "ContentAnalyzer",
    "IntelligenceGatheringService",
]
