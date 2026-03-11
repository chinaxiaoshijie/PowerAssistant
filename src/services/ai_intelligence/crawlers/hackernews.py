"""Hacker News crawler for AI-related posts.

Fetches posts from Hacker News API.
"""

from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional

import structlog

from src.services.ai_intelligence.base import BaseCrawler, CrawlResult

logger = structlog.get_logger()


class HackerNewsCrawler(BaseCrawler):
    """Crawler for Hacker News AI-related posts.

    Fetches top and new stories from Hacker News,
    filtering for AI-related content.
    """

    # AI-related keywords to filter posts
    AI_KEYWORDS = [
        "ai", "artificial intelligence", "machine learning", "ml",
        "deep learning", "neural network", "llm", "gpt", "claude",
        "openai", "anthropic", "transformer", "pytorch", "tensorflow",
    ]

    def __init__(self, config: Optional[dict] = None):
        """Initialize Hacker News crawler."""
        super().__init__(config)
        self.keywords = self.config.get("keywords", self.AI_KEYWORDS)

    def get_source_name(self) -> str:
        return "Hacker News"

    def get_source_type(self) -> str:
        return "hackernews"

    def _is_ai_related(self, title: str) -> bool:
        """Check if post title is AI-related.

        Args:
            title: Post title

        Returns:
            True if AI-related
        """
        title_lower = title.lower()
        return any(keyword in title_lower for keyword in self.keywords)

    async def _fetch_item(self, item_id: int) -> Optional[dict]:
        """Fetch a single item from HN API.

        Args:
            item_id: Item ID

        Returns:
            Item data or None
        """
        try:
            url = f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
            return await self.fetch_json(url)
        except Exception as e:
            self._logger.debug("fetch_item_failed", item_id=item_id, error=str(e))
            return None

    async def _fetch_top_stories(self, limit: int = 100) -> list:
        """Fetch top story IDs.

        Args:
            limit: Maximum stories to fetch

        Returns:
            List of story IDs
        """
        try:
            url = "https://hacker-news.firebaseio.com/v0/topstories.json"
            story_ids = await self.fetch_json(url)
            return story_ids[:limit] if story_ids else []
        except Exception as e:
            self._logger.error("fetch_top_stories_failed", error=str(e))
            return []

    async def crawl(
        self,
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> AsyncGenerator[CrawlResult, None]:
        """Crawl Hacker News for AI-related posts.

        Args:
            since: Only fetch posts newer than this
            limit: Maximum posts

        Yields:
            CrawlResult objects
        """
        self._logger.info(
            "crawling_hackernews",
            since=since,
            limit=limit,
        )

        if since is None:
            since = datetime.utcnow() - timedelta(hours=24)

        # Fetch top stories
        story_ids = await self._fetch_top_stories(limit=100)

        count = 0
        for story_id in story_ids:
            if count >= limit:
                break

            # Fetch story details
            story = await self._fetch_item(story_id)
            if not story:
                continue

            # Check if story
            if story.get("type") != "story":
                continue

            title = story.get("title", "")

            # Check if AI-related
            if not self._is_ai_related(title):
                continue

            # Check time
            story_time = story.get("time")
            if story_time:
                story_datetime = datetime.fromtimestamp(story_time)
                if story_datetime < since:
                    continue

            # Create result
            result = CrawlResult(
                title=title,
                url=story.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
                content=story.get("text", ""),
                author=story.get("by"),
                published_at=datetime.fromtimestamp(story_time) if story_time else None,
                external_id=str(story_id),
                metadata={
                    "score": story.get("score"),
                    "descendants": story.get("descendants"),
                    "type": story.get("type"),
                },
            )

            yield result
            count += 1

        self._logger.info("hackernews_crawl_completed", total_posts=count)
