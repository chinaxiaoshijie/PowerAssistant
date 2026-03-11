"""Base classes for intelligence gathering crawlers."""

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncGenerator, Dict, List, Optional

import aiohttp
import structlog

from src.config.ai_settings import ai_engine_settings

logger = structlog.get_logger()


@dataclass
class CrawlResult:
    """Result of crawling a single item."""

    title: str
    url: str
    content: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    external_id: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    def compute_hash(self) -> str:
        """Compute content hash for deduplication."""
        content = f"{self.title}:{self.url}:{self.content or ''}"
        return hashlib.md5(content.encode()).hexdigest()


class BaseCrawler(ABC):
    """Abstract base class for intelligence crawlers.

    All crawlers must implement:
    - crawl(): Main crawling method
    - get_source_name(): Return human-readable source name
    - get_source_type(): Return source type identifier
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialize crawler with configuration.

        Args:
            config: Source-specific configuration
        """
        self.config = config or {}
        self._logger = logger.bind(
            crawler=self.__class__.__name__,
            source=self.get_source_name(),
        )
        self._session: Optional[aiohttp.ClientSession] = None

    @abstractmethod
    def get_source_name(self) -> str:
        """Return human-readable source name."""
        pass

    @abstractmethod
    def get_source_type(self) -> str:
        """Return source type identifier."""
        pass

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(
                total=ai_engine_settings.request_timeout
            )
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def fetch_url(
        self,
        url: str,
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> str:
        """Fetch URL content.

        Args:
            url: URL to fetch
            headers: Optional headers
            params: Optional query parameters

        Returns:
            Response text
        """
        session = await self._get_session()

        self._logger.debug("fetching_url", url=url)

        async with session.get(url, headers=headers, params=params) as response:
            response.raise_for_status()
            text = await response.text()
            self._logger.debug("url_fetched", url=url, size=len(text))
            return text

    async def fetch_json(
        self,
        url: str,
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict:
        """Fetch URL and parse JSON.

        Args:
            url: URL to fetch
            headers: Optional headers
            params: Optional query parameters

        Returns:
            Parsed JSON
        """
        session = await self._get_session()

        self._logger.debug("fetching_json", url=url)

        async with session.get(url, headers=headers, params=params) as response:
            response.raise_for_status()
            data = await response.json()
            self._logger.debug("json_fetched", url=url)
            return data

    @abstractmethod
    async def crawl(
        self,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> AsyncGenerator[CrawlResult, None]:
        """Crawl intelligence items.

        Args:
            since: Only fetch items newer than this time
            limit: Maximum items to fetch

        Yields:
            CrawlResult objects
        """
        pass

    async def close(self) -> None:
        """Close crawler resources."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._logger.debug("session_closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
