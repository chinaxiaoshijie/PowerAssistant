"""GitHub Trending crawler for AI repositories."""

from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional

import structlog

from src.services.ai_intelligence.base import BaseCrawler, CrawlResult

logger = structlog.get_logger()


class GitHubTrendingCrawler(BaseCrawler):
    """Crawler for GitHub trending AI repositories.

    Fetches trending repositories from GitHub and extracts
    AI/ML related projects.
    """

    # GitHub topics to search for AI-related repos
    AI_TOPICS = [
        "artificial-intelligence",
        "machine-learning",
        "deep-learning",
        "neural-network",
        "llm",
        "large-language-models",
        "transformers",
        "pytorch",
        "tensorflow",
        "openai",
        "anthropic",
        "langchain",
    ]

    def __init__(self, config: Optional[dict] = None):
        """Initialize GitHub crawler.

        Args:
            config: Configuration with optional 'token' for GitHub API
        """
        super().__init__(config)
        self.token = self.config.get("token")

    def get_source_name(self) -> str:
        return "GitHub Trending"

    def get_source_type(self) -> str:
        return "github"

    async def crawl(
        self,
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> AsyncGenerator[CrawlResult, None]:
        """Crawl trending AI repositories from GitHub.

        Uses GitHub Search API to find recently updated AI repositories.
        """
        self._logger.info(
            "crawling_github",
            since=since,
            limit=limit,
        )

        # Use GitHub Search API
        # Search for repos updated in last 7 days with AI topics
        if since is None:
            since = datetime.utcnow() - timedelta(days=7)

        date_str = since.strftime("%Y-%m-%d")

        # Build search query
        topics_query = " OR ".join([f"topic:{t}" for t in self.AI_TOPICS[:6]])
        query = f"({topics_query}) pushed:>{date_str}"

        url = "https://api.github.com/search/repositories"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Malong-Management-Assistant",
        }

        if self.token:
            headers["Authorization"] = f"token {self.token}"

        params = {
            "q": query,
            "sort": "updated",
            "order": "desc",
            "per_page": min(limit, 100),
        }

        try:
            data = await self.fetch_json(url, headers=headers, params=params)

            items = data.get("items", [])
            self._logger.info("github_repos_found", count=len(items))

            for repo in items[:limit]:
                result = CrawlResult(
                    title=repo.get("name", ""),
                    url=repo.get("html_url", ""),
                    content=repo.get("description", ""),
                    author=repo.get("owner", {}).get("login"),
                    published_at=datetime.fromisoformat(
                        repo.get("pushed_at", "").replace("Z", "+00:00")
                    ) if repo.get("pushed_at") else None,
                    external_id=str(repo.get("id")),
                    metadata={
                        "stars": repo.get("stargazers_count", 0),
                        "language": repo.get("language"),
                        "forks": repo.get("forks_count", 0),
                        "topics": repo.get("topics", []),
                        "full_name": repo.get("full_name"),
                    },
                )

                yield result

        except Exception as e:
            self._logger.error("github_crawl_failed", error=str(e))
            raise
