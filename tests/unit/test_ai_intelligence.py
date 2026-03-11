"""Tests for AI Intelligence service."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.models.ai_intelligence import IntelligenceItem, IntelligenceReport
from src.services.ai_intelligence import IntelligenceGatheringService
from src.services.ai_intelligence.base import CrawlResult


class TestIntelligenceGatheringService:
    """Test Intelligence Gathering Service."""

    @pytest.fixture
    def service(self, db_session):
        """Create intelligence service."""
        return IntelligenceGatheringService(db_session)

    @pytest.mark.asyncio
    async def test_crawl_and_store_arxiv(self, service, sample_crawl_results):
        """Test crawling and storing arxiv items."""
        with patch('src.services.ai_intelligence.crawlers.arxiv.ArxivCrawler.crawl') as mock_crawl:
            mock_crawl.return_value = self._async_generator(sample_crawl_results)

            items = await service.crawl_and_store("arxiv", limit=10)

            assert len(items) == 2
            assert items[0].title == "Test Paper 1"
            assert items[0].source_type == "arxiv"

    @pytest.mark.asyncio
    async def test_crawl_and_store_deduplication(self, service, sample_crawl_results):
        """Test duplicate detection during crawl."""
        # First crawl
        with patch('src.services.ai_intelligence.crawlers.arxiv.ArxivCrawler.crawl') as mock_crawl:
            mock_crawl.return_value = self._async_generator(sample_crawl_results)
            items1 = await service.crawl_and_store("arxiv", limit=10)

        # Second crawl with same items
        with patch('src.services.ai_intelligence.crawlers.arxiv.ArxivCrawler.crawl') as mock_crawl:
            mock_crawl.return_value = self._async_generator(sample_crawl_results)
            items2 = await service.crawl_and_store("arxiv", limit=10)

        # Second crawl should skip duplicates
        assert len(items1) == 2
        assert len(items2) == 0

    @pytest.mark.asyncio
    async def test_analyze_pending_items(self, service, sample_intelligence_item):
        """Test analyzing pending items."""
        # Create unprocessed item
        item = sample_intelligence_item
        item.is_processed = False
        item.content = "Test content for analysis"
        service._db.add(item)
        await service._db.commit()

        with patch.object(service._analyzer, 'analyze') as mock_analyze:
            mock_analyze.return_value = {
                "category": "research_paper",
                "summary": "Test summary",
                "key_points": ["point1"],
                "tags": ["AI"],
                "technologies": ["PyTorch"],
                "relevance_score": 0.85,
                "relevance_reasoning": "Highly relevant",
                "action_items": ["Action 1"],
            }

            count = await service.analyze_pending_items(batch_size=10)

            assert count == 1
            assert item.is_processed is True
            assert item.category == "research_paper"
            assert item.relevance_score == 0.85

    @pytest.mark.asyncio
    async def test_generate_daily_report(self, service, sample_intelligence_item):
        """Test generating daily report."""
        # Add processed items
        item = sample_intelligence_item
        item.is_processed = True
        item.created_at = datetime.utcnow()
        service._db.add(item)
        await service._db.commit()

        report = await service.generate_daily_report()

        assert report.report_type == "daily"
        assert len(report.highlights) >= 0
        assert report.period_start is not None
        assert report.period_end is not None

    @pytest.mark.asyncio
    async def test_get_high_relevance_items(self, service, sample_intelligence_item):
        """Test getting high relevance items."""
        # Create items with different relevance scores
        for i, score in enumerate([0.9, 0.6, 0.8]):
            item = IntelligenceItem(
                source_type="arxiv",
                source_name="arXiv",
                external_id=f"arxiv_{i}",
                title=f"Test Item {i}",
                url=f"https://example.com/{i}",
                content_hash=f"hash_{i}",
                category="research_paper",
                relevance_score=score,
                is_processed=True,
                is_read=False,
            )
            service._db.add(item)

        await service._db.commit()

        items = await service.get_high_relevance_items(threshold=0.7, limit=10)

        assert len(items) == 2  # 0.9 and 0.8
        assert all(item.relevance_score >= 0.7 for item in items)

    def _async_generator(self, items):
        """Helper to create async generator."""
        async def gen():
            for item in items:
                yield item
        return gen()


class TestContentAnalyzer:
    """Test Content Analyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create content analyzer."""
        from src.services.ai_intelligence.analyzer import ContentAnalyzer
        return ContentAnalyzer()

    @pytest.mark.asyncio
    async def test_analyze(self, analyzer, sample_crawl_results):
        """Test content analysis."""
        result = sample_crawl_results[0]

        with patch('src.services.ai_intelligence.analyzer.ai_engine') as mock_ai:
            mock_ai.generate_text = AsyncMock(return_value=json.dumps({
                "category": "research_paper",
                "summary": "Test summary",
                "key_points": ["Point 1"],
                "tags": ["AI"],
                "technologies": ["PyTorch"],
                "relevance_score": 0.85,
                "relevance_reasoning": "Reasoning",
                "action_items": ["Action"],
            }))

            analysis = await analyzer.analyze(result)

            assert analysis["category"] == "research_paper"
            assert analysis["relevance_score"] == 0.85

    @pytest.mark.asyncio
    async def test_analyze_invalid_json(self, analyzer, sample_crawl_results):
        """Test handling invalid JSON response."""
        result = sample_crawl_results[0]

        with patch('src.services.ai_intelligence.analyzer.ai_engine') as mock_ai:
            mock_ai.generate_text = AsyncMock(return_value="Invalid JSON")

            analysis = await analyzer.analyze(result)

            # Should return default structure on parse failure
            assert "summary" in analysis


import json
