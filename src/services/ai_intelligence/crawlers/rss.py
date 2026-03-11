"""RSS/Atom feed crawler for AI blogs and news.

Fetches and parses RSS feeds from various sources.
"""

from datetime import datetime, timedelta
from typing import AsyncGenerator, List, Optional

import structlog

from src.services.ai_intelligence.base import BaseCrawler, CrawlResult

logger = structlog.get_logger()


class RSSCrawler(BaseCrawler):
    """Crawler for RSS/Atom feeds.

    Supports multiple feed formats and extracts relevant content.
    """

    # Default AI-related RSS feeds
    DEFAULT_FEEDS = [
        # OpenAI Blog
        "https://openai.com/blog/rss.xml",
        # Anthropic
        "https://www.anthropic.com/blog/rss.xml",
        # Google AI Blog
        "https://ai.googleblog.com/feeds/posts/default",
        # Microsoft AI Blog
        "https://blogs.microsoft.com/ai/feed/",
        # PyTorch Blog
        "https://pytorch.org/blog/atom.xml",
        # Hugging Face Blog
        "https://huggingface.co/blog/feed.xml",
    ]

    def __init__(self, config: Optional[dict] = None):
        """Initialize RSS crawler.

        Args:
            config: Configuration with 'feeds' list
        """
        super().__init__(config)
        self.feeds = self.config.get("feeds", self.DEFAULT_FEEDS)

    def get_source_name(self) -> str:
        return "RSS Feeds"

    def get_source_type(self) -> str:
        return "rss"

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats from RSS feeds.

        Args:
            date_str: Date string

        Returns:
            Parsed datetime or None
        """
        from email.utils import parsedate_to_datetime

        if not date_str:
            return None

        formats = [
            "%a, %d %b %Y %H:%M:%S %z",  # RFC 2822
            "%Y-%m-%dT%H:%M:%S%z",  # ISO 8601
            "%Y-%m-%dT%H:%M:%SZ",  # ISO 8601 UTC
            "%Y-%m-%d %H:%M:%S",  # Simple format
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # Try email utils for RFC 2822
        try:
            return parsedate_to_datetime(date_str)
        except Exception:
            pass

        return None

    def _extract_text_from_html(self, html: str) -> str:
        """Extract plain text from HTML.

        Args:
            html: HTML content

        Returns:
            Plain text
        """
        try:
            from html.parser import HTMLParser

            class TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text = []
                    self.skip = False

                def handle_starttag(self, tag, attrs):
                    if tag in ["script", "style"]:
                        self.skip = True

                def handle_endtag(self, tag):
                    if tag in ["script", "style"]:
                        self.skip = False

                def handle_data(self, data):
                    if not self.skip:
                        self.text.append(data)

            extractor = TextExtractor()
            extractor.feed(html)
            return " ".join(extractor.text)

        except Exception:
            return html

    async def _parse_feed(
        self,
        feed_url: str,
        since: datetime,
        limit: int,
    ) -> AsyncGenerator[CrawlResult, None]:
        """Parse a single RSS feed.

        Args:
            feed_url: Feed URL
            since: Only fetch entries newer than this
            limit: Maximum entries
        """
        try:
            # Fetch feed content
            content = await self.fetch_url(feed_url)

            # Try to parse as XML
            import xml.etree.ElementTree as ET

            root = ET.fromstring(content.encode("utf-8"))

            # Determine feed type (RSS or Atom)
            ns = {"": root.tag.split("}")[0].strip("{")} if "}" in root.tag else {}

            entries = []

            if root.tag.endswith("feed"):  # Atom
                entries = root.findall(".//entry", ns)
            else:  # RSS
                entries = root.findall(".//item", ns) or root.findall(".//item")

            count = 0

            for entry in entries:
                if count >= limit:
                    break

                # Extract fields
                title_elem = (
                    entry.find("title", ns)
                    or entry.find(".//{http://www.w3.org/2005/Atom}title")
                )
                title = title_elem.text if title_elem is not None else "No Title"

                link_elem = (
                    entry.find("link", ns)
                    or entry.find(".//{http://www.w3.org/2005/Atom}link")
                )
                if link_elem is not None:
                    url = link_elem.get("href", "")
                    if not url:
                        url = link_elem.text or ""
                else:
                    url = ""

                desc_elem = (
                    entry.find("description", ns)
                    or entry.find("summary", ns)
                    or entry.find(".//{http://www.w3.org/2005/Atom}summary")
                )
                content_html = desc_elem.text if desc_elem is not None else ""
                content = self._extract_text_from_html(content_html)

                author_elem = (
                    entry.find("author", ns)
                    or entry.find("creator", ns)
                    or entry.find(".//{http://www.w3.org/2005/Atom}author")
                )
                author = None
                if author_elem is not None:
                    name_elem = author_elem.find("name", ns)
                    author = name_elem.text if name_elem is not None else author_elem.text

                date_elem = (
                    entry.find("pubDate", ns)
                    or entry.find("published", ns)
                    or entry.find(".//{http://www.w3.org/2005/Atom}published")
                )
                published_at = None
                if date_elem is not None:
                    published_at = self._parse_date(date_elem.text)

                # Skip old entries
                if published_at and published_at < since:
                    continue

                # Generate external ID from URL or title
                import hashlib
                external_id = hashlib.md5(url.encode()).hexdigest()[:12]

                result = CrawlResult(
                    title=title,
                    url=url,
                    content=content[:2000],  # Limit content length
                    author=author,
                    published_at=published_at,
                    external_id=external_id,
                    metadata={
                        "feed_url": feed_url,
                        "feed_type": "atom" if "atom" in root.tag.lower() else "rss",
                    },
                )

                yield result
                count += 1

        except Exception as e:
            self._logger.error(
                "feed_parse_failed",
                feed_url=feed_url,
                error=str(e),
            )

    async def crawl(
        self,
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> AsyncGenerator[CrawlResult, None]:
        """Crawl RSS feeds.

        Args:
            since: Only fetch entries newer than this
            limit: Maximum total entries

        Yields:
            CrawlResult objects
        """
        self._logger.info(
            "crawling_rss",
            feeds_count=len(self.feeds),
            since=since,
            limit=limit,
        )

        if since is None:
            since = datetime.utcnow() - timedelta(hours=24)

        count = 0
        limit_per_feed = max(1, limit // len(self.feeds))

        for feed_url in self.feeds:
            if count >= limit:
                break

            self._logger.debug("parsing_feed", url=feed_url)

            try:
                async for result in self._parse_feed(
                    feed_url, since, limit_per_feed
                ):
                    yield result
                    count += 1

                    if count >= limit:
                        break

            except Exception as e:
                self._logger.error(
                    "feed_crawl_failed",
                    feed_url=feed_url,
                    error=str(e),
                )

        self._logger.info("rss_crawl_completed", total_entries=count)
