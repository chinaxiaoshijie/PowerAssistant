"""Reddit crawler for AI-related subreddits.

Fetches posts from AI/ML related subreddits.
Note: Requires Reddit API credentials.
"""

from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional

import structlog

from src.services.ai_intelligence.base import BaseCrawler, CrawlResult

logger = structlog.get_logger()


class RedditCrawler(BaseCrawler):
    """Crawler for Reddit AI-related subreddits.

    Fetches hot and new posts from configured subreddits.
    Requires Reddit API credentials.
    """

    # AI/ML related subreddits
    DEFAULT_SUBREDDITS = [
        "MachineLearning",
        "artificial",
        "LocalLLaMA",
        "OpenAI",
        "ClaudeAI",
        "singularity",
        "ChatGPT",
        "AI_Agents",
    ]

    def __init__(self, config: Optional[dict] = None):
        """Initialize Reddit crawler.

        Args:
            config: Configuration with 'client_id', 'client_secret', 'user_agent'
        """
        super().__init__(config)
        self.subreddits = self.config.get("subreddits", self.DEFAULT_SUBREDDITS)
        self.client_id = self.config.get("client_id")
        self.client_secret = self.config.get("client_secret")
        self.user_agent = self.config.get(
            "user_agent",
            "MalongManagementBot/1.0"
        )
        self._access_token: Optional[str] = None

    def get_source_name(self) -> str:
        return "Reddit"

    def get_source_type(self) -> str:
        return "reddit"

    async def _get_access_token(self) -> str:
        """Get Reddit API access token."""
        if self._access_token:
            return self._access_token

        if not self.client_id or not self.client_secret:
            raise ValueError("Reddit API credentials not configured")

        import base64

        auth = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        headers = {
            "Authorization": f"Basic {auth}",
            "User-Agent": self.user_agent,
        }

        data = {
            "grant_type": "client_credentials",
        }

        session = await self._get_session()

        async with session.post(
            "https://www.reddit.com/api/v1/access_token",
            headers=headers,
            data=data,
        ) as response:
            response.raise_for_status()
            token_data = await response.json()
            self._access_token = token_data.get("access_token")
            return self._access_token

    async def _fetch_subreddit(
        self,
        subreddit: str,
        since: datetime,
        limit: int,
    ) -> AsyncGenerator[CrawlResult, None]:
        """Fetch posts from a subreddit.

        Args:
            subreddit: Subreddit name
            since: Only fetch posts newer than this
            limit: Maximum posts
        """
        token = await self._get_access_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": self.user_agent,
        }

        # Fetch hot and new posts
        for sort in ["hot", "new"]:
            url = f"https://oauth.reddit.com/r/{subreddit}/{sort}"

            params = {
                "limit": min(limit, 25),
                "t": "day" if sort == "hot" else None,
            }

            try:
                data = await self.fetch_json(url, headers=headers, params=params)

                posts = data.get("data", {}).get("children", [])

                for post in posts:
                    post_data = post.get("data", {})

                    # Check post time
                    created_utc = post_data.get("created_utc")
                    if created_utc:
                        post_time = datetime.fromtimestamp(created_utc)
                        if post_time < since:
                            continue

                    result = CrawlResult(
                        title=post_data.get("title", ""),
                        url=f"https://www.reddit.com{post_data.get('permalink', '')}",
                        content=post_data.get("selftext", ""),
                        author=post_data.get("author"),
                        published_at=datetime.fromtimestamp(created_utc) if created_utc else None,
                        external_id=post_data.get("id"),
                        metadata={
                            "subreddit": subreddit,
                            "score": post_data.get("score"),
                            "num_comments": post_data.get("num_comments"),
                            "is_self": post_data.get("is_self"),
                            "domain": post_data.get("domain"),
                        },
                    )

                    yield result

            except Exception as e:
                self._logger.error(
                    "subreddit_fetch_failed",
                    subreddit=subreddit,
                    sort=sort,
                    error=str(e),
                )

    async def crawl(
        self,
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> AsyncGenerator[CrawlResult, None]:
        """Crawl Reddit for AI-related posts.

        Args:
            since: Only fetch posts newer than this
            limit: Maximum total posts

        Yields:
            CrawlResult objects
        """
        self._logger.info(
            "crawling_reddit",
            subreddits=self.subreddits,
            since=since,
            limit=limit,
        )

        if since is None:
            since = datetime.utcnow() - timedelta(hours=24)

        count = 0
        limit_per_sub = max(1, limit // len(self.subreddits))

        for subreddit in self.subreddits:
            if count >= limit:
                break

            try:
                async for result in self._fetch_subreddit(
                    subreddit, since, limit_per_sub
                ):
                    yield result
                    count += 1

                    if count >= limit:
                        break

            except Exception as e:
                self._logger.error(
                    "subreddit_crawl_failed",
                    subreddit=subreddit,
                    error=str(e),
                )

        self._logger.info("reddit_crawl_completed", total_posts=count)
